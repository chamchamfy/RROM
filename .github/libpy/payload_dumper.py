#!/usr/bin/env python3
import os
import argparse
import struct
import bz2
import lzma
import sys
import hashlib
import json
import lz4.block
import zstandard as zstd
import brotli
import bsdiff4
import update_metadata_pb2 as um
from multiprocessing import Pool, Manager

def decompress_multi_xz(data):
    results = []
    while data:
        dec = lzma.LZMADecompressor(format=lzma.FORMAT_AUTO)
        try:
            res = dec.decompress(data)
            results.append(res)
            data = dec.unused_data
        except Exception:
            break
    return b''.join(results)

def bytes_to_readable(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

def process_partition(part_raw, args_dict, data_offset, block_size, counter, debug=False):
    name = "Unknown"
    try:
        part = um.PartitionUpdate()
        part.ParseFromString(part_raw)
        name = part.partition_name

        out_path = os.path.join(args_dict['out'], f"{name}.img")
        old_img_path = os.path.join(args_dict['old'], f"{name}.img")

        if debug:
            print(f"\n[DEBUG] Bắt đầu xử lý phân vùng: {name}")
            print(f"[DEBUG] Kích thước phân vùng: {part.new_partition_info.size} bytes")
            print(f"[DEBUG] Hash mong đợi: {part.new_partition_info.hash.hex() if part.new_partition_info.hash else 'None'}")

        with open(out_path, 'wb') as f_out:
            f_out.truncate(part.new_partition_info.size)

        with open(out_path, 'r+b') as f_out:
            with open(args_dict['payload_path'], 'rb') as f_pay:
                for op in part.operations:
                    f_pay.seek(data_offset + op.data_offset)
                    data = f_pay.read(op.data_length)
                    out_data = b''

                    if debug:
                        print(f"\n[DEBUG] Operation: {op.type}")
                        print(f"[DEBUG]   data_offset: {op.data_offset}")
                        print(f"[DEBUG]   data_length: {op.data_length}")
                        print(f"[DEBUG]   dst_extents: {[ (ext.start_block, ext.num_blocks) for ext in op.dst_extents ]}")

                    if op.type == um.InstallOperation.REPLACE:
                        out_data = data
                    elif op.type == um.InstallOperation.REPLACE_BZ:
                        out_data = bz2.decompress(data)
                    elif op.type == um.InstallOperation.REPLACE_XZ:
                        out_data = decompress_multi_xz(data)
                    elif op.type == 5:
                        out_data = lz4.block.decompress(data, uncompressed_size=op.dst_length)
                    elif op.type == 7:
                        dctx = zstd.ZstdDecompressor()
                        out_data = dctx.decompress(data, max_output_size=op.dst_length)
                    elif op.type == 8:
                        out_data = brotli.decompress(data)
                    elif op.type == um.InstallOperation.ZERO:
                        for ext in op.dst_extents:
                            f_out.seek(ext.start_block * block_size)
                            f_out.write(b'\x00' * (ext.num_blocks * block_size))
                        continue
                    elif op.type in [um.InstallOperation.SOURCE_COPY, um.InstallOperation.SOURCE_BSDIFF, um.InstallOperation.BROTLI_BSDIFF]:
                        if not args_dict['diff']:
                            raise Exception(f"Lỗi: Phân vùng {name} là Delta nhưng chưa bật --diff")
                        if not os.path.exists(old_img_path):
                            raise FileNotFoundError(f"Lỗi: Thiếu file gốc {name}.img trong thư mục '{args_dict['old']}'")

                        with open(old_img_path, 'rb') as f_old:
                            src_data = b''
                            for ext in op.src_extents:
                                f_old.seek(ext.start_block * block_size)
                                src_data += f_old.read(ext.num_blocks * block_size)

                            if op.type == um.InstallOperation.SOURCE_COPY:
                                out_data = src_data
                            elif op.type == um.InstallOperation.SOURCE_BSDIFF:
                                out_data = bsdiff4.patch(src_data, data)
                            elif op.type == um.InstallOperation.BROTLI_BSDIFF:
                                out_data = bsdiff4.patch(src_data, brotli.decompress(data))

                    if debug:
                        print(f"[DEBUG]   Kích thước dữ liệu đầu ra: {len(out_data)} bytes")
                        print(f"[DEBUG]   Kích thước mong đợi: {op.dst_length} bytes")

                    data_ptr = 0
                    for ext in op.dst_extents:
                        f_out.seek(ext.start_block * block_size)
                        length = ext.num_blocks * block_size
                        f_out.write(out_data[data_ptr : data_ptr + length])
                        data_ptr += length

            f_out.flush()
            os.fsync(f_out.fileno())

        sha256 = hashlib.sha256()
        with open(out_path, 'rb') as f_verify:
            while chunk := f_verify.read(1024*1024):
                sha256.update(chunk)

        status = ""
        if part.new_partition_info.hash and sha256.digest() != part.new_partition_info.hash:
            status = f" | Lỗi: Sai HASH (tính toán: {sha256.hexdigest()}, mong đợi: {part.new_partition_info.hash.hex()})"
            if debug:
                print(f"[DEBUG] {name}: SHA256 MISMATCH!")
                print(f"[DEBUG]   Hash tính toán: {sha256.hexdigest()}")
                print(f"[DEBUG]   Hash mong đợi: {part.new_partition_info.hash.hex()}")

        sys.stdout.write(f"[OK] {name}.img{status}\n")
        sys.stdout.flush()
        counter.value += 1
        return True

    except Exception as e:
        sys.stdout.write(f"[ERROR] {name} | Lỗi: {str(e)}\n")
        sys.stdout.flush()
        return False

class PayloadDumper:
    def __init__(self, args):
        self.args = args
        try:
            self.payload_file = open(args.payload, 'rb')
        except FileNotFoundError:
            print(f"Lỗi: Không tìm thấy file {args.payload}"); sys.exit(1)
        self._parse_header()

    def _parse_header(self):
        magic = self.payload_file.read(4)
        if magic != b'CrAU':
            print("Lỗi: Định dạng payload.bin không hợp lệ"); sys.exit(1)
        self.version = struct.unpack('>Q', self.payload_file.read(8))[0]
        self.manifest_size = struct.unpack('>Q', self.payload_file.read(8))[0]
        self.sig_size = struct.unpack('>I', self.payload_file.read(4))[0] if self.version > 1 else 0
        self.manifest_data = self.payload_file.read(self.manifest_size)
        self.payload_file.read(self.sig_size)
        self.data_offset = self.payload_file.tell()
        self.manifest = um.DeltaArchiveManifest()
        self.manifest.ParseFromString(self.manifest_data)

    def dump_metadata_json(self, output_dir):
        metadata = {
            "security_patch_level": "N/A",
            "block_size": self.manifest.block_size,
            "minor_version": 0,
            "max_timestamp": int(self.manifest.max_timestamp) if self.manifest.max_timestamp else 0,
            "dynamic_partition_metadata": {
                "groups": [],
                "groups_count": 0,
                "snapshot_enabled": True,
                "vabc_enabled": True,
                "vabc_compression_param": "lz4",
                "cow_version": 3,
                "compression_factor": 65536
            },
            "apex_info": [],
            "apex_info_count": 0,
            "partitions": [],
            "partitions_count": len(self.manifest.partitions),
            "signatures_offset": 0,
            "signatures_size": 0,
            "total_payload_size": os.path.getsize(self.args.payload),
            "total_payload_size_readable": bytes_to_readable(os.path.getsize(self.args.payload)),
            "total_operations_count": 0,
            "global_operation_stats": []
        }

        if self.manifest.dynamic_partition_metadata:
            for group in self.manifest.dynamic_partition_metadata.groups:
                metadata["dynamic_partition_metadata"]["groups"].append({
                    "name": group.name,
                    "size": group.size,
                    "size_readable": bytes_to_readable(group.size),
                    "partition_names": list(group.partition_names),
                    "partition_count": len(group.partition_names)
                })
            metadata["dynamic_partition_metadata"]["groups_count"] = len(self.manifest.dynamic_partition_metadata.groups)

        global_op_stats = {}
        total_ops = 0
        total_data_size = 0

        for p in self.manifest.partitions:
            partition_info = {
                "partition_name": p.partition_name,
                "size_in_blocks": p.new_partition_info.size // self.manifest.block_size,
                "size_in_bytes": p.new_partition_info.size,
                "size_readable": bytes_to_readable(p.new_partition_info.size),
                "hash": p.new_partition_info.hash.hex() if p.new_partition_info.hash else "",
                "partition_type": p.partition_name.split('_')[0],
                "operations_count": len(p.operations),
                "compression_type": "none",
                "encryption": "none",
                "block_size": self.manifest.block_size,
                "total_blocks": p.new_partition_info.size // self.manifest.block_size,
                "merge_operations_count": 0,
                "signature_count": 0,
                "operation_type_stats": [],
                "total_data_size": 0,
                "total_data_size_readable": "0 B",
                "num_src_extents": 0,
                "num_dst_extents": 0
            }

            op_stats = {}
            partition_data_size = 0
            compression_types = set()

            for op in p.operations:
                op_type = self._get_operation_type_name(op.type)
                op_stats[op_type] = op_stats.get(op_type, {"count": 0, "total_data_size": 0})
                op_stats[op_type]["count"] += 1
                op_stats[op_type]["total_data_size"] += op.data_length
                partition_data_size += op.data_length
                compression_types.add(self._get_compression_type(op.type))

                global_op_stats[op_type] = global_op_stats.get(op_type, {"count": 0, "total_data_size": 0})
                global_op_stats[op_type]["count"] += 1
                global_op_stats[op_type]["total_data_size"] += op.data_length
                total_ops += 1
                total_data_size += op.data_length

            partition_info["operation_type_stats"] = [
                {"operation_type": k, "count": v["count"], "total_data_size": v["total_data_size"]}
                for k, v in op_stats.items()
            ]
            partition_info["total_data_size"] = partition_data_size
            partition_info["total_data_size_readable"] = bytes_to_readable(partition_data_size)
            partition_info["compression_type"] = "mixed" if len(compression_types) > 1 else next(iter(compression_types), "none")

            for op in p.operations:
                partition_info["num_dst_extents"] += len(op.dst_extents)
                partition_info["num_src_extents"] += len(op.src_extents) if op.src_extents else 0

            metadata["partitions"].append(partition_info)

        metadata["total_operations_count"] = total_ops
        metadata["global_operation_stats"] = [
            {"operation_type": k, "count": v["count"], "total_data_size": v["total_data_size"]}
            for k, v in global_op_stats.items()
        ]

        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        out_path = os.path.join(output_dir, "metadata.json")
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"[*] Đã xuất Metadata vào: {out_path}")

    def _get_compression_type(self, op_type):
        if op_type == um.InstallOperation.REPLACE_BZ:
            return "bz2"
        elif op_type == um.InstallOperation.REPLACE_XZ:
            return "xz"
        elif op_type == 5:
            return "lz4"
        elif op_type == 7:
            return "zstd"
        elif op_type == 8:
            return "brotli"
        else:
            return "none"

    def _get_operation_type_name(self, op_type):
        op_names = {
            um.InstallOperation.REPLACE: "REPLACE",
            um.InstallOperation.REPLACE_BZ: "REPLACE_BZ",
            um.InstallOperation.REPLACE_XZ: "REPLACE_XZ",
            um.InstallOperation.SOURCE_COPY: "SOURCE_COPY",
            um.InstallOperation.SOURCE_BSDIFF: "SOURCE_BSDIFF",
            um.InstallOperation.ZERO: "ZERO",
            5: "REPLACE_LZ4",
            7: "REPLACE_ZSTD",
            8: "REPLACE_BROTLI",
            um.InstallOperation.BROTLI_BSDIFF: "BROTLI_BSDIFF"
        }
        return op_names.get(op_type, str(op_type))

    def run(self):
        if self.args.metadata:
            self.dump_metadata_json(self.args.out)
            return

        if self.args.list:
            print(f"{'Phân vùng':<25} | {'Kích thước':<15}")
            for p in self.manifest.partitions:
                print(f"{p.partition_name:<25} | {p.new_partition_info.size}")
            return

        payload_dir = os.path.dirname(os.path.abspath(self.args.payload))
        self.dump_metadata_json(payload_dir)

        debug_partitions = {
            "vendor.img", "vendor_boot.img", "vendor_dlkm.img",
            "vm-bootsys.img", "xbl.img", "xbl_config.img", "xbl_ramdump.img"
        }

        if not os.path.exists(self.args.out):
            os.makedirs(self.args.out, exist_ok=True)

        work_list = self.manifest.partitions
        if self.args.images:
            work_list = [p for p in work_list if p.partition_name in self.args.images]

        print(f"[*] Đang trích xuất {len(work_list)} phân vùng với {self.args.threads} luồng xử lý")

        manager = Manager()
        sync_counter = manager.Value('i', 0)
        args_dict = {
            'payload_path': self.args.payload,
            'out': self.args.out,
            'old': self.args.old,
            'diff': self.args.diff
        }

        tasks = [
            (
                p.SerializeToString(),
                args_dict,
                self.data_offset,
                self.manifest.block_size,
                sync_counter,
                self.args.debug and (p.partition_name in debug_partitions or not debug_partitions)
            )
            for p in work_list
        ]

        with Pool(processes=self.args.threads) as pool:
            pool.starmap(process_partition, tasks)

        print(f"[*] Hoàn tất {sync_counter.value}/{len(work_list)} phân vùng.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Payload Dumper CC")
    parser.add_argument("payload", help="Đường dẫn file payload.bin")
    parser.add_argument("-o", "--out", default="output", help="Thư mục đầu ra cho phân vùng")
    parser.add_argument("-t", "--threads", type=int, default=1, help="Số luồng")
    parser.add_argument("-i", "--images", nargs='+', help="Tên phân vùng cụ thể")
    parser.add_argument("-l", "--list", action="store_true", help="Liệt kê phân vùng")
    parser.add_argument("-m", "--metadata", action="store_true", help="Xuất metadata.json vào thư mục chỉ định")
    parser.add_argument("-d", "--debug", action="store_true", help="Bật chế độ debug chi tiết")
    parser.add_argument("--diff", action="store_true", help="Bật chế độ Delta OTA")
    parser.add_argument("--old", default="old", help="Thư mục file gốc cho diff")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    try:
        args = parser.parse_args()
        PayloadDumper(args).run()
    except Exception as e:
        print(f"Lỗi: {e}")
