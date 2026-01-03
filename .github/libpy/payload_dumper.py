#!/usr/bin/env python3
import os
import argparse
import struct
import bz2
import lzma
import sys
import json
import hashlib
import lz4.block
import zstandard as zstd
import bsdiff4
import update_metadata_pb2
from multiprocessing import Pool, Manager
from google.protobuf.json_format import MessageToJson

# Hàm Worker xử lý từng phân vùng
def process_partition(part_raw, args_dict, data_offset, block_size, counter):
    import update_metadata_pb2 as um
    part = um.PartitionUpdate()
    part.ParseFromString(part_raw)
    name = part.partition_name
    
    out_path = os.path.join(args_dict['out'], f"{name}.img")
    old_img_path = os.path.join(args_dict['old'], f"{name}.img")
    dctx = zstd.ZstdDecompressor()
    sha256 = hashlib.sha256()

    try:
        with open(args_dict['payload_path'], 'rb') as f_pay, open(out_path, 'wb') as f_out:
            for op in part.operations:
                if op.data_offset is not None:
                    f_pay.seek(data_offset + op.data_offset)
                data = f_pay.read(op.data_length) if op.data_length else b''

                # --- Xử lý các định dạng nén (Bao gồm LZ4) ---
                if op.type == 0: # REPLACE
                    out_data = data
                elif op.type == 1: # REPLACE_BZ
                    out_data = bz2.decompress(data)
                elif op.type == 8: # REPLACE_XZ
                    out_data = lzma.decompress(data)
                elif op.type == 5: # REPLACE_LZ4 (Thêm hỗ trợ LZ4)
                    # LZ4 block thường yêu cầu kích thước đích để giải nén chính xác
                    out_data = lz4.block.decompress(data, uncompressed_size=op.dst_length)
                elif op.type == 6: # REPLACE_ZSTD
                    out_data = dctx.decompress(data, max_output_size=op.dst_length)
                elif op.type in [3, 5] and args_dict['diff']: # BSDIFF / SOURCE_BSDIFF
                    if os.path.exists(old_img_path):
                        with open(old_img_path, 'rb') as f_old:
                            src_io = b''
                            for ext in op.src_extents:
                                f_old.seek(ext.start_block * block_size)
                                src_io += f_old.read(ext.num_blocks * block_size)
                            out_data = bsdiff4.patch(src_io, data)
                    else:
                        raise FileNotFoundError(f"Thiếu file gốc: {old_img_path}")
                else:
                    out_data = data

                f_out.write(out_data)
                sha256.update(out_data)

        # Kiểm tra Hash sau khi giải nén
        if part.new_partition_info.hash:
            if sha256.digest() != part.new_partition_info.hash:
                print(f"[!] CẢNH BÁO: {name}.img không khớp Hash SHA256")
        
        print(f"[THÀNH CÔNG] {name}.img")
        counter.value += 1
        return True
    except Exception as e:
        print(f"[LỖI] {name}.img | Chi tiết: {e}")
        return False

class PayloadDumper:
    def __init__(self, args):
        self.args = args
        try:
            self.payload_file = open(args.payload, 'rb')
        except FileNotFoundError:
            print(f"[!] Lỗi: Không tìm thấy file {args.payload}")
            sys.exit(1)
        self._parse_header()

    def _parse_header(self):
        magic = self.payload_file.read(4)
        if magic != b'CrAU':
            print("[!] Lỗi: Định dạng payload.bin không hợp lệ.")
            sys.exit(1)
        version = struct.unpack('>Q', self.payload_file.read(8))[0]
        manifest_size = struct.unpack('>Q', self.payload_file.read(8))[0]
        sig_size = struct.unpack('>I', self.payload_file.read(4))[0] if version > 1 else 0
        self.manifest_data = self.payload_file.read(manifest_size)
        self.payload_file.read(sig_size)
        self.data_offset = self.payload_file.tell()
        
        self.manifest = update_metadata_pb2.DeltaArchiveManifest()
        self.manifest.ParseFromString(self.manifest_data)

    def dump_metadata(self):
        meta_file = os.path.join(self.args.out, "metadata.json")
        try:
            json_string = MessageToJson(self.manifest)
            with open(meta_file, "w", encoding="utf-8") as f:
                f.write(json_string)
            print(f"[*] Đã xuất Metadata: {meta_file}")
        except Exception as e:
            print(f"[!] Lỗi trích xuất Metadata: {e}")

    def run(self):
        if not os.path.exists(self.args.out):
            os.makedirs(self.args.out)
        
        if self.args.metadata:
            self.dump_metadata()

        work_list = [p for p in self.manifest.partitions if not self.args.images or p.partition_name in self.args.images]
        total = len(work_list)
        
        print(f"[*] Đang xử lý {total} phân vùng với {self.args.threads} luồng.")
        
        manager = Manager()
        success_counter = manager.Value('i', 0)
        
        args_dict = {
            'payload_path': self.args.payload,
            'out': self.args.out,
            'diff': self.args.diff,
            'old': self.args.old
        }

        tasks = [(p.SerializeToString(), args_dict, self.data_offset, self.manifest.block_size, success_counter) for p in work_list]

        with Pool(processes=self.args.threads) as pool:
            pool.starmap(process_partition, tasks)

        print(f"\nĐã trích xuất thành công: {success_counter.value}/{total} phân vùng.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Android Payload Dumper Pro (LZ4 Support)")
    parser.add_argument("payload", help="Đường dẫn file payload.bin")
    parser.add_argument("-o", "--out", default="output", help="Thư mục đầu ra")
    parser.add_argument("-t", "--threads", type=int, default=2, help="Số luồng đa nhân")
    parser.add_argument("-i", "--images", nargs='+', help="Các phân vùng cụ thể")
    parser.add_argument("-m", "--metadata", action="store_true", help="Xuất Metadata JSON")
    parser.add_argument("--diff", action="store_true", help="Chế độ Differential")
    parser.add_argument("--old", default="old", help="Thư mục chứa ảnh gốc")

    args = parser.parse_args()
    PayloadDumper(args).run()
        
