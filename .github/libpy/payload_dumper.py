#!/usr/bin/env python3
import os
import argparse
import struct
import bz2
import lzma
import sys
import hashlib
import lz4.block
import zstandard as zstd
import brotli
import bsdiff4
import update_metadata_pb2
from multiprocessing import Pool, Manager
from google.protobuf.json_format import MessageToJson

def decompress_multi_bz2(data):
    results = []
    while data:
        dec = bz2.BZ2Decompressor()
        try:
            res = dec.decompress(data)
            results.append(res)
            data = dec.unused_data
        except Exception:
            break
    return b''.join(results)

def decompress_multi_xz(data):
    try:
        return lzma.decompress(data)
    except lzma.LZMAError:
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

def process_partition(part_raw, args_dict, data_offset, block_size, counter):
    import update_metadata_pb2 as um
    part = um.PartitionUpdate()
    part.ParseFromString(part_raw)
    name = part.partition_name
    
    out_path = os.path.join(args_dict['out'], f"{name}.img")
    old_img_path = os.path.join(args_dict['old'], f"{name}.img")
    
    try:
        with open(out_path, 'wb+') as f_out:
            with open(args_dict['payload_path'], 'rb') as f_pay:
                for op in part.operations:
                    f_pay.seek(data_offset + op.data_offset)
                    data = f_pay.read(op.data_length)
                    out_data = b''
                    
                    if op.type == um.InstallOperation.REPLACE:
                        out_data = data
                    elif op.type == um.InstallOperation.REPLACE_BZ:
                        out_data = decompress_multi_bz2(data)
                    elif op.type == um.InstallOperation.REPLACE_XZ:
                        out_data = decompress_multi_xz(data)
                    elif op.type == 5: # REPLACE_LZ4
                        out_data = lz4.block.decompress(data, uncompressed_size=op.dst_length)
                    elif op.type == 7: # REPLACE_ZSTD
                        dctx = zstd.ZstdDecompressor()
                        out_data = dctx.decompress(data, max_output_size=op.dst_length if op.dst_length else 0)
                    elif op.type == 8: # REPLACE_BROTLI
                        out_data = brotli.decompress(data)
                    elif op.type == um.InstallOperation.ZERO:
                        out_data = b'\x00' * sum(e.num_blocks for e in op.dst_extents) * block_size
                    elif op.type in [um.InstallOperation.SOURCE_COPY, um.InstallOperation.SOURCE_BSDIFF, um.InstallOperation.BROTLI_BSDIFF]:
                        if not os.path.exists(old_img_path):
                            raise FileNotFoundError(f"Thiếu file gốc trong thư mục '{args_dict['old']}'")
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
                    for extent in op.dst_extents:
                        f_out.seek(extent.start_block * block_size)
                        length = extent.num_blocks * block_size
                        f_out.write(out_data[data_ptr : data_ptr + length])
                        data_ptr += length

        sha256 = hashlib.sha256()
        with open(out_path, 'rb') as f_verify:
            while chunk := f_verify.read(1024*1024):
                sha256.update(chunk)

        status = ""
        if part.new_partition_info.hash and sha256.digest() != part.new_partition_info.hash:
            status = " | Sai HASH có thể lỗi file"
        
        sys.stdout.write(f"[OK] {name}.img{status}\n")
        sys.stdout.flush()
        counter.value += 1
        return True
    except FileNotFoundError as e:
        sys.stdout.write(f"[ERROR]: {name}.img | Lỗi: {str(e)}\n")
        return False
    except Exception as e:
        sys.stdout.write(f"[ERROR]: {name}.img | Lỗi: {str(e)}\n")
        return False

class PayloadDumper:
    def __init__(self, args):
        self.args = args
        try:
            self.payload_file = open(args.payload, 'rb')
        except FileNotFoundError:
            print(f"[ERROR]: Không tìm thấy file {args.payload}"); sys.exit(1)
        self._parse_header()

    def _parse_header(self):
        magic = self.payload_file.read(4)
        if magic != b'CrAU':
            print("[ERROR]: payload.bin không hợp lệ."); sys.exit(1)
        self.version = struct.unpack('>Q', self.payload_file.read(8))[0]
        self.manifest_size = struct.unpack('>Q', self.payload_file.read(8))[0]
        self.sig_size = struct.unpack('>I', self.payload_file.read(4))[0] if self.version > 1 else 0
        self.manifest_data = self.payload_file.read(self.manifest_size)
        self.payload_file.read(self.sig_size)
        self.data_offset = self.payload_file.tell()
        self.manifest = update_metadata_pb2.DeltaArchiveManifest()
        self.manifest.ParseFromString(self.manifest_data)

    def run(self):
        if not os.path.exists(self.args.out): os.makedirs(self.args.out)
        
        if self.args.metadata:
            meta_path = os.path.join(self.args.out, "metadata.json")
            with open(meta_path, "w", encoding="utf-8") as f:
                f.write(MessageToJson(self.manifest, indent=2))
            print(f"[*] Đã xuất Metadata: {meta_path}")
            return

        if self.args.list:
            print(f"{'Phân vùng':<25} | {'Kích thước (Bytes)':<15}")
            for part in self.manifest.partitions:
                print(f"{part.partition_name:<25} | {part.new_partition_info.size:<15}")
            print(f"\nTổng cộng: {len(self.manifest.partitions)} phân vùng.")
            return

        work_list = [p for p in self.manifest.partitions if not self.args.images or p.partition_name in self.args.images]
        print(f"[*] Đang xử lý {len(work_list)} phân vùng với {self.args.threads} luồng")
        
        manager = Manager()
        counter = manager.Value('i', 0)
        args_dict = {'payload_path': self.args.payload, 'out': self.args.out, 'old': self.args.old}
        tasks = [(p.SerializeToString(), args_dict, self.data_offset, self.manifest.block_size, counter) for p in work_list]

        with Pool(processes=self.args.threads) as pool:
            pool.starmap(process_partition, tasks)
        print(f"[*] Hoàn tất {counter.value}/{len(work_list)} phân vùng.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Payload Dumper CC")
    parser.add_argument("payload", help="Đường dẫn file payload.bin")
    parser.add_argument("-o", "--out", default="output", help="Thư mục xuất file")
    parser.add_argument("-t", "--threads", type=int, default=1, help="Số luồng")
    parser.add_argument("-i", "--images", nargs='+', help="Phân vùng cụ thể")
    parser.add_argument("-l", "--list", action="store_true", help="Liệt kê phân vùng")
    parser.add_argument("-m", "--metadata", action="store_true", help="Chỉ xuất metadata.json")
    parser.add_argument("--diff", action="store_true", help="Chế độ Delta OTA")
    parser.add_argument("--old", default="old", help="Thư mục chứa file ảnh cũ")
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
        
    args = parser.parse_args()
    PayloadDumper(args).run()
                        
