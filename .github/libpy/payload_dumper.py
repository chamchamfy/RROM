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
import bsdiff4
import update_metadata_pb2
from multiprocessing import Pool, Manager

def write_to_dst(op, out_file, data, block_size):
    offset = 0
    for ext in op.dst_extents:
        length = ext.num_blocks * block_size
        chunk = data[offset : offset + length]
        if len(chunk) < length:
            chunk += b'\x00' * (length - len(chunk))
        out_file.seek(ext.start_block * block_size)
        out_file.write(chunk)
        offset += length

def get_source_data(op, old_file, block_size):
    src_io = io.BytesIO()
    for ext in op.src_extents:
        old_file.seek(ext.start_block * block_size)
        src_io.write(old_file.read(ext.num_blocks * block_size))
    return src_io.getvalue()

# Hàm Worker xử lý phân vùng
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
                if op.data_offset:
                    f_pay.seek(data_offset + op.data_offset)
                data = f_pay.read(op.data_length) if op.data_length else b''

                # --- Xử lý định dạng theo Enum ---
                if op.type == 0: # REPLACE
                    out_data = data
                elif op.type == 1: # REPLACE_BZ
                    out_data = bz2.decompress(data)
                elif op.type == 8: # REPLACE_XZ
                    out_data = lzma.decompress(data)
                elif op.type == 5: # REPLACE_LZ4 (Số hiệu tùy chỉnh/mới)
                    out_data = lz4.block.decompress(data, uncompressed_size=op.dst_length)
                elif op.type == 6: # REPLACE_ZSTD (Zstandard)
                    out_data = dctx.decompress(data, max_output_size=op.dst_length)
                elif op.type in [3, 5] and args_dict['diff']: # BSDIFF / SOURCE_BSDIFF
                    with open(old_img_path, 'rb') as f_old:
                        src_io = b''
                        for ext in op.src_extents:
                            f_old.seek(ext.start_block * block_size)
                            src_io += f_old.read(ext.num_blocks * block_size)
                        out_data = bsdiff4.patch(src_io, data)
                elif op.type == 10 and args_dict['diff']: # BROTLI_BSDIFF
                    import brotli
                    with open(old_img_path, 'rb') as f_old:
                        src_io = b''
                        for ext in op.src_extents:
                            f_old.seek(ext.start_block * block_size)
                            src_io += f_old.read(ext.num_blocks * block_size)
                        out_data = bsdiff4.patch(src_io, brotli.decompress(data))
                else:
                    continue

                f_out.write(out_data)
                sha256.update(out_data)

        # Kiểm tra Hash
        final_hash = sha256.digest()
        if part.new_partition_info.hash:
            if final_hash != part.new_partition_info.hash:
                print(f"[!] CẢNH BÁO: {name}.img sai Hash SHA256!")
                return False
        
        print(f"[THÀNH CÔNG] {name}.img")
        counter.value += 1
        return True

    except Exception as e:
        print(f"[LỖI] {name}.img | Chi tiết: {e}")
        return False

class PayloadDumper:
    def __init__(self, args):
        self.args = args
        self.payload_file = open(args.payload, 'rb')
        self._parse_header()

    def _parse_header(self):
        magic = self.payload_file.read(4)
        version = struct.unpack('>Q', self.payload_file.read(8))[0]
        manifest_size = struct.unpack('>Q', self.payload_file.read(8))[0]
        sig_size = struct.unpack('>I', self.payload_file.read(4))[0] if version > 1 else 0
        manifest_data = self.payload_file.read(manifest_size)
        self.payload_file.read(sig_size)
        self.data_offset = self.payload_file.tell()
        self.manifest = update_metadata_pb2.DeltaArchiveManifest()
        self.manifest.ParseFromString(manifest_data)

    def run(self):
        if not os.path.exists(self.args.out): os.makedirs(self.args.out)
        
        work_list = [p for p in self.manifest.partitions if not self.args.images or p.partition_name in self.args.images]
        total_count = len(work_list)
        
        print(f"[*] Đang xử lý {total_count} phân vùng với {self.args.threads} luồng.")
        
        # Sử dụng Manager để đếm số thành công từ các tiến trình con
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

        print(f"HOÀN TẤT: Đã trích xuất thành công {success_counter.value}/{total_count} phân vùng.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Payload Dumper Pro")
    parser.add_argument("payload", help="Đường dẫn payload.bin")
    parser.add_argument("-o", "--out", default="output", help="Thư mục xuất")
    parser.add_argument("-t", "--threads", type=int, default=2, help="Số luồng")
    parser.add_argument("-i", "--images", nargs='+', help="Phân vùng cụ thể")
    parser.add_argument("--diff", action="store_true", help="Chế độ Delta")
    parser.add_argument("--old", default="old", help="Thư mục cũ")

    args = parser.parse_args()
    PayloadDumper(args).run()
