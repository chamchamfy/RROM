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

# --- HÀM DEBUG RIÊNG BIỆT (XÓA NẾU KHÔNG CẦN) ---
def print_debug_info(name, op_index, op, block_size):
    """Hàm chuyên biệt để in chi tiết các thao tác khi bật -d"""
    op_types = {0: "NOP", 1: "REPLACE", 2: "REPLACE_BZ", 3: "REPLACE_XZ", 4: "ZERO", 5: "REPLACE_LZ4", 6: "SOURCE_COPY", 7: "REPLACE_ZSTD", 8: "REPLACE_BROTLI"}
    t_name = op_types.get(op.type, f"TYPE_{op.type}")
    sys.stdout.write(f"  [Op {op_index}] {t_name:<12} | Offset: {op.data_offset:<10} | Size: {op.data_length}\n")

def decompress_multi_xz(data):
    results = []
    while data:
        dec = lzma.LZMADecompressor(format=lzma.FORMAT_AUTO)
        try:
            res = dec.decompress(data)
            results.append(res)
            data = dec.unused_data
        except Exception: break
    return b''.join(results)

def process_partition(part_raw, args_dict, data_offset, block_size, counter):
    name = "Unknown"
    debug = args_dict.get('debug', False)
    try:
        part = um.PartitionUpdate()
        part.ParseFromString(part_raw)
        name = part.partition_name
        
        if debug:
            sys.stdout.write(f"\n[DEBUG] Bắt đầu xử lý: {name} ({part.new_partition_info.size} bytes)\n")

        out_path = os.path.join(args_dict['out'], f"{name}.img")
        old_img_path = os.path.join(args_dict['old'], f"{name}.img")
        
        with open(out_path, 'wb') as f_out:
            f_out.truncate(part.new_partition_info.size)
        
        with open(out_path, 'r+b') as f_out:
            with open(args_dict['payload_path'], 'rb') as f_pay:
                for i, op in enumerate(part.operations):
                    # GỌI HÀM DEBUG (Có thể xóa dòng này)
                    if debug: print_debug_info(name, i, op, block_size)
                    
                    f_pay.seek(data_offset + op.data_offset)
                    data = f_pay.read(op.data_length)
                    out_data = b''
                    
                    if op.type == um.InstallOperation.REPLACE:
                        out_data = data
                    elif op.type == um.InstallOperation.REPLACE_BZ:
                        out_data = bz2.decompress(data)
                    elif op.type == um.InstallOperation.REPLACE_XZ:
                        out_data = decompress_multi_xz(data)
                    elif op.type == 5: # REPLACE_LZ4
                        out_data = lz4.block.decompress(data, uncompressed_size=op.dst_length)
                    elif op.type == 7: # REPLACE_ZSTD
                        dctx = zstd.ZstdDecompressor()
                        out_data = dctx.decompress(data, max_output_size=op.dst_length)
                    elif op.type == 8: # REPLACE_BROTLI
                        out_data = brotli.decompress(data)
                    elif op.type == um.InstallOperation.ZERO:
                        for ext in op.dst_extents:
                            f_out.seek(ext.start_block * block_size)
                            f_out.write(b'\x00' * (ext.num_blocks * block_size))
                        continue
                    
                    elif op.type in [um.InstallOperation.SOURCE_COPY, um.InstallOperation.SOURCE_BSDIFF, um.InstallOperation.BROTLI_BSDIFF]:
                        if not args_dict['diff']:
                            raise Exception(f"Lỗi: Phân vùng {name} cần --diff")
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
        actual_h = sha256.hexdigest()
        expect_h = part.new_partition_info.hash.hex() if part.new_partition_info.hash else ""
        
        if expect_h and actual_h != expect_h:
            status = f" | Lỗi: Sai HASH (tính toán: {actual_h}, mong đợi: {expect_h})"
        
        sys.stdout.write(f"[OK] {name}.img{status}\n")
        sys.stdout.flush()
        counter.value += 1
        return True
    except Exception as e:
        sys.stdout.write(f"[ERROR]: {name} | Lỗi: {str(e)}\n")
        return False

class PayloadDumper:
    def __init__(self, args):
        self.args = args
        try:
            self.payload_file = open(args.payload, 'rb')
        except FileNotFoundError:
            print(f"[ERROR]: Lỗi: Không thấy file {args.payload}"); sys.exit(1)
        self._parse_header()

    def _parse_header(self):
        magic = self.payload_file.read(4)
        if magic != b'CrAU':
            print("[ERROR]: Lỗi: Magic không hợp lệ"); sys.exit(1)
        self.version = struct.unpack('>Q', self.payload_file.read(8))[0]
        self.manifest_size = struct.unpack('>Q', self.payload_file.read(8))[0]
        self.sig_size = struct.unpack('>I', self.payload_file.read(4))[0] if self.version > 1 else 0
        self.manifest_data = self.payload_file.read(self.manifest_size)
        self.payload_file.read(self.sig_size)
        self.data_offset = self.payload_file.tell()
        self.manifest = um.DeltaArchiveManifest()
        self.manifest.ParseFromString(self.manifest_data)

    def dump_metadata_full(self):
        groups = []
        if self.manifest.dynamic_partition_metadata:
            for g in self.manifest.dynamic_partition_metadata.groups:
                partition_list = list(g.partition_names)
                groups.append({
                    "group_name": g.name,
                    "size": g.size,
                    "partition_count": len(partition_list),
                    "partitions": partition_list
                })

        parts_info = []
        for p in self.manifest.partitions:
            parts_info.append({
                "partition_name": p.partition_name,
                "size_bytes": p.new_partition_info.size,
                "sha256_hash": p.new_partition_info.hash.hex() if p.new_partition_info.hash else "N/A"
            })

        output_data = {
            "block_size": self.manifest.block_size,
            "super_groups_info": {
                "total_groups": len(groups),
                "groups": groups
            },
            "all_partitions_detail": parts_info
        }

        out_path = os.path.join(self.args.out, "metadata.json")
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"[*] Đã xuất Metadata đầy đủ: {out_path}")

    def run(self):
        if not os.path.exists(self.args.out): os.makedirs(self.args.out)
        if self.args.metadata: self.dump_metadata_full(); return
        
        if self.args.list:
            print(f"{'Phân vùng':<25} | {'Kích thước':<15} | {'Hash'}")
            for p in self.manifest.partitions:
                h = p.new_partition_info.hash.hex()[:10] + "..." if p.new_partition_info.hash else "N/A"
                print(f"{p.partition_name:<25} | {p.new_partition_info.size:<15} | {h}")
            return

        work_list = [p for p in self.manifest.partitions if not self.args.images or p.partition_name in self.args.images]
        manager = Manager()
        sync_counter = manager.Value('i', 0)
        args_dict = {
            'payload_path': self.args.payload, 'out': self.args.out, 
            'old': self.args.old, 'diff': self.args.diff, 'debug': self.args.debug
        }
        
        num_threads = 1 if self.args.debug else self.args.threads
        with Pool(processes=num_threads) as pool:
            pool.starmap(process_partition, [(p.SerializeToString(), args_dict, self.data_offset, self.manifest.block_size, sync_counter) for p in work_list])
            
        print(f"[*] Hoàn tất {sync_counter.value}/{len(work_list)} phân vùng.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Payload Dumper CC - Final Edition")
    parser.add_argument("payload", help="Đường dẫn file payload.bin")
    parser.add_argument("-o", "--out", default="output", help="Thư mục xuất")
    parser.add_argument("-t", "--threads", type=int, default=os.cpu_count())
    parser.add_argument("-i", "--images", nargs='+', help="Phân vùng cụ thể")
    parser.add_argument("-l", "--list", action="store_true", help="Liệt kê")
    parser.add_argument("-m", "--metadata", action="store_true", help="Xuất metadata")
    parser.add_argument("-d", "--debug", action="store_true", help="Chế độ debug")
    parser.add_argument("--diff", action="store_true", help="Delta OTA")
    parser.add_argument("--old", default="old", help="Thư mục file gốc")

    if len(sys.argv) == 1:
        parser.print_help(); sys.exit(1)

    args = parser.parse_args()
    PayloadDumper(args).run()
