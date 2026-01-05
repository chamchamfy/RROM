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
from google.protobuf.json_format import MessageToJson

# Hàm giải nén XZ nhiều luồng dữ liệu
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
    try:
        part = um.PartitionUpdate()
        part.ParseFromString(part_raw)
        name = part.partition_name
        
        out_path = os.path.join(args_dict['out'], f"{name}.img")
        old_img_path = os.path.join(args_dict['old'], f"{name}.img")
        
        # Tạo file mới và cấp phát dung lượng thực tế
        with open(out_path, 'wb') as f_out:
            f_out.truncate(part.new_partition_info.size)
        
        with open(out_path, 'r+b') as f_out:
            with open(args_dict['payload_path'], 'rb') as f_pay:
                for op in part.operations:
                    f_pay.seek(data_offset + op.data_offset)
                    data = f_pay.read(op.data_length)
                    out_data = b''
                    
                    # Các kiểu giải nén
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
                    
                    # Xử lý Delta/Diff OTA
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
                    
                    # Ghi dữ liệu vào đúng vị trí extents
                    data_ptr = 0
                    for ext in op.dst_extents:
                        f_out.seek(ext.start_block * block_size)
                        length = ext.num_blocks * block_size
                        f_out.write(out_data[data_ptr : data_ptr + length])
                        data_ptr += length

            # Đồng bộ dữ liệu xuống đĩa (Quan trọng trên Ubuntu)
            f_out.flush()
            os.fsync(f_out.fileno())

        # Kiểm tra HASH SHA256
        sha256 = hashlib.sha256()
        with open(out_path, 'rb') as f_verify:
            while chunk := f_verify.read(1024*1024):
                sha256.update(chunk)

        status = ""
        if part.new_partition_info.hash and sha256.digest() != part.new_partition_info.hash:
            status = " | Lỗi: Sai HASH"
        
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

    def dump_metadata_json(self):
        super_meta = []
        if self.manifest.dynamic_partition_metadata:
            for group in self.manifest.dynamic_partition_metadata.groups:
                super_meta.append({
                    "group_name": group.name,
                    "group_size_bytes": group.size,
                    "contains_partitions": list(group.partition_names)
                })

        meta_data = {
            "block_size": self.manifest.block_size,
            "super_info": super_meta,
            "partitions": [
                {
                    "name": p.partition_name,
                    "size_bytes": p.new_partition_info.size,
                    "hash_sha256": p.new_partition_info.hash.hex() if p.new_partition_info.hash else ""
                } for p in self.manifest.partitions
            ]
        }
        out_path = os.path.join(self.args.out, "metadata.json")
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(meta_data, f, indent=2)
        print(f"[*] Đã xuất Metadata vào: {out_path}")

    def run(self):
        if not os.path.exists(self.args.out): os.makedirs(self.args.out)
        
        if self.args.metadata:
            self.dump_metadata_json()
            return

        if self.args.list:
            print(f"{'Phân vùng':<25} | {'Kích thước':<15}")
            for p in self.manifest.partitions:
                print(f"{p.partition_name:<25} | {p.new_partition_info.size}")
            return

        work_list = [p for p in self.manifest.partitions if not self.args.images or p.partition_name in self.args.images]
        print(f"[*] Đang trích xuất {len(work_list)} phân vùng với{self.args.threads} luồng xử lý")
        
        manager = Manager()
        sync_counter = manager.Value('i', 0)
        args_dict = {
            'payload_path': self.args.payload, 
            'out': self.args.out, 
            'old': self.args.old, 
            'diff': self.args.diff
        }
        
        tasks = [(p.SerializeToString(), args_dict, self.data_offset, self.manifest.block_size, sync_counter) for p in work_list]

        with Pool(processes=self.args.threads) as pool:
            pool.starmap(process_partition, tasks)
            
        print(f"[*] Hoàn tất {sync_counter.value}/{len(work_list)} phân vùng.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Payload Dumper CC")
    parser.add_argument("payload", help="Đường dẫn file payload.bin")
    parser.add_argument("-o", "--out", default="output", help="Thư mục đầu ra")
    parser.add_argument("-t", "--threads", type=int, default=1, help="Số luồng")
    parser.add_argument("-i", "--images", nargs='+', help="Tên phân vùng cụ thể")
    parser.add_argument("-l", "--list", action="store_true", help="Liệt kê phân vùng")
    parser.add_argument("-m", "--metadata", action="store_true", help="Xuất thông tin metadata")
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
