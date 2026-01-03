#!/usr/bin/env python3
import struct
import bz2
import sys
import argparse
import io
import os
import lzma
import json
from multiprocessing import Pool

# Kiểm tra thư viện hỗ trợ
def check_lib(lib_name):
    try:
        return __import__(lib_name)
    except ImportError:
        return None

bsdiff4 = check_lib('bsdiff4')
brotli = check_lib('brotli')
zstd = check_lib('zstandard')

try:
    import update_metadata_pb2 as um
except ImportError:
    sys.exit("Lỗi: Không tìm thấy update_metadata_pb2.py. Vui lòng đặt cùng thư mục!")

def u32(x): return struct.unpack('>I', x)[0]
def u64(x): return struct.unpack('>Q', x)[0]

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

def process_partition_worker(part_raw, args_dict, data_offset, block_size):
    part = um.PartitionUpdate()
    part.ParseFromString(part_raw)
    out_path = os.path.join(args_dict['out'], f"{part.partition_name}.img")
    
    sys.stdout.write(f"Đang xử lý {part.partition_name} ")
    sys.stdout.flush()

    with open(args_dict['payload_path'], 'rb') as payload_file:
        old_file = None
        if args_dict['diff']:
            old_path = os.path.join(args_dict['old'], f"{part.partition_name}.img")
            if os.path.exists(old_path): old_file = open(old_path, 'rb')

        try:
            with open(out_path, 'wb') as out_file:
                for i, op in enumerate(part.operations):
                    if op.data_offset:
                        payload_file.seek(data_offset + op.data_offset)
                    data = payload_file.read(op.data_length) if op.data_length else b''

                    # --- Xử lý đầy đủ định dạng dựa trên Enum của bạn ---
                    if op.type == 0: # REPLACE
                        write_to_dst(op, out_file, data, block_size)
                    elif op.type == 1: # REPLACE_BZ
                        write_to_dst(op, out_file, bz2.decompress(data), block_size)
                    elif op.type == 8: # REPLACE_XZ
                        write_to_dst(op, out_file, lzma.decompress(data), block_size)
                    elif op.type == 6: # ZERO
                        for ext in op.dst_extents:
                            out_file.seek(ext.start_block * block_size)
                            out_file.write(b'\x00' * ext.num_blocks * block_size)
                    elif op.type == 4 and old_file: # SOURCE_COPY
                        write_to_dst(op, out_file, get_source_data(op, old_file, block_size), block_size)
                    elif op.type in [3, 5] and old_file: # BSDIFF / SOURCE_BSDIFF
                        if bsdiff4:
                            patched = bsdiff4.patch(get_source_data(op, old_file, block_size), data)
                            write_to_dst(op, out_file, patched, block_size)
                    elif op.type == 10 and old_file: # BROTLI_BSDIFF
                        if brotli and bsdiff4:
                            patch_raw = brotli.decompress(data)
                            patched = bsdiff4.patch(get_source_data(op, old_file, block_size), patch_raw)
                            write_to_dst(op, out_file, patched, block_size)
                    elif op.type == 14 and zstd: # REPLACE_ZSTD
                        dctx = zstd.ZstdDecompressor()
                        write_to_dst(op, out_file, dctx.decompress(data), block_size)
                    
                    if i % 10 == 0:
                        sys.stdout.write(".")
                        sys.stdout.flush()
        finally:
            if old_file: old_file.close()
            
    sys.stdout.write(" OK\n")
    sys.stdout.flush()
    return part.partition_name

class PayloadDumper:
    def __init__(self, args):
        self.args = args
        self.payload_file = open(args.payloadfile, 'rb')
        self._parse_header()

    def _parse_header(self):
        magic = self.payload_file.read(4)
        if magic != b'CrAU': sys.exit("Lỗi: Magic bytes không khớp.")
        version = u64(self.payload_file.read(8))
        manifest_size = u64(self.payload_file.read(8))
        sig_size = u32(self.payload_file.read(4)) if version > 1 else 0
        self.manifest_raw = self.payload_file.read(manifest_size)
        self.payload_file.read(sig_size)
        self.data_offset = self.payload_file.tell()
        self.dam = um.DeltaArchiveManifest()
        self.dam.ParseFromString(self.manifest_raw)

    def extract_metadata(self):
        meta_path = os.path.join(self.args.out, "metadata.json")
        meta_data = {
            "block_size": self.dam.block_size,
            "partitions": [{"name": p.partition_name, "ops": len(p.operations), "hash": p.new_partition_info.hash.hex() if p.new_partition_info.hash else ""} for p in self.dam.partitions]
        }
        with open(meta_path, "w") as f:
            json.dump(meta_data, f, indent=4)
        print(f"[*] Đã trích xuất metadata vào: {meta_path}")

    def run(self):
        if not os.path.exists(self.args.out): os.makedirs(self.args.out)
        if self.args.metadata: self.extract_metadata()

        tasks = []
        images = self.args.images.split(",") if self.args.images else []
        args_dict = {'payload_path': self.args.payloadfile, 'out': self.args.out, 'diff': self.args.diff, 'old': self.args.old}

        for part in self.dam.partitions:
            if not images or part.partition_name in images:
                tasks.append((part.SerializeToString(), args_dict, self.data_offset, self.dam.block_size))

        print(f"[*] Đang sử dụng {self.args.threads} luồng...")
        with Pool(processes=self.args.threads) as pool:
            pool.starmap(process_partition_worker, tasks)
        print("\n[+] Hoàn tất!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Full Format Payload Dumper')
    parser.add_argument('payloadfile', help='Đường dẫn file payload.bin')
    parser.add_argument('-o', '--out', default='output', help='Thư mục đầu ra')
    parser.add_argument('-m', '--metadata', action='store_true', help='Trích xuất Metadata JSON')
    parser.add_argument('-i', '--images', default="", help='Lọc phân vùng (vd: boot,system)')
    parser.add_argument('-t', '--threads', type=int, default=2, help='Số luồng đa nhân (mặc định: 2)')
    parser.add_argument('--diff', action='store_true', help='Chế độ cập nhật Diff')
    parser.add_argument('--old', default='old', help='Thư mục ảnh gốc cho Diff')

    args = parser.parse_args()
    PayloadDumper(args).run()
    
