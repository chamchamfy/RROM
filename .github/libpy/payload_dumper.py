#!/usr/bin/env python3
import struct
import bz2
import sys
import argparse
import io
import os
import lzma

# Kiểm tra và import các thư viện hỗ trợ
try:
    import bsdiff4
except ImportError:
    sys.exit("Lỗi: Vui lòng cài đặt bsdiff4 (pip install bsdiff4)")

try:
    import brotli
except ImportError:
    brotli = None

try:
    import zstandard as zstd
except ImportError:
    zstd = None

try:
    import update_metadata_pb2 as um
except ImportError:
    sys.exit("Lỗi: Không tìm thấy update_metadata_pb2.py. Hãy đặt nó cùng thư mục!")

def u32(x): return struct.unpack('>I', x)[0]
def u64(x): return struct.unpack('>Q', x)[0]

class PayloadDumper:
    def __init__(self, args):
        self.args = args
        self.payload_file = args.payloadfile
        self.block_size = 0
        self.data_offset = 0
        self._parse_header()

    def _parse_header(self):
        print("[*] Đang đọc cấu trúc file payload.bin...")
        magic = self.payload_file.read(4)
        if magic != b'CrAU':
            sys.exit("Lỗi: File không hợp lệ (Sai Magic Bytes).")

        version = u64(self.payload_file.read(8))
        manifest_size = u64(self.payload_file.read(8))
        
        signature_size = 0
        if version > 1:
            signature_size = u32(self.payload_file.read(4))

        manifest_raw = self.payload_file.read(manifest_size)
        self.payload_file.read(signature_size) 
        
        self.data_offset = self.payload_file.tell()
        
        self.dam = um.DeltaArchiveManifest()
        self.dam.ParseFromString(manifest_raw)
        self.block_size = self.dam.block_size
        print(f"[*] Kích thước Block: {self.block_size}")

    def _get_source_data(self, op, old_file):
        if not old_file: return b''
        src_io = io.BytesIO()
        for ext in op.src_extents:
            old_file.seek(ext.start_block * self.block_size)
            src_io.write(old_file.read(ext.num_blocks * self.block_size))
        return src_io.getvalue()

    def _write_dst(self, op, out_file, data):
        offset = 0
        for ext in op.dst_extents:
            length = ext.num_blocks * self.block_size
            chunk = data[offset : offset + length]
            if len(chunk) < length:
                chunk += b'\x00' * (length - len(chunk))
            out_file.seek(ext.start_block * self.block_size)
            out_file.write(chunk)
            offset += length

    def process_op(self, op, out_file, old_file):
        if op.data_offset:
            self.payload_file.seek(self.data_offset + op.data_offset)
        data = self.payload_file.read(op.data_length) if op.data_length else b''

        if op.type == 0: # REPLACE
            self._write_dst(op, out_file, data)
        elif op.type == 1: # REPLACE_BZ
            self._write_dst(op, out_file, bz2.decompress(data))
        elif op.type == 8: # REPLACE_XZ
            self._write_dst(op, out_file, lzma.decompress(data))
        elif op.type == 6: # ZERO
            for ext in op.dst_extents:
                out_file.seek(ext.start_block * self.block_size)
                out_file.write(b'\x00' * ext.num_blocks * self.block_size)
        elif op.type == 4: # SOURCE_COPY
            if old_file:
                self._write_dst(op, out_file, self._get_source_data(op, old_file))
        elif op.type == 5: # SOURCE_BSDIFF
            if old_file:
                patched = bsdiff4.patch(self._get_source_data(op, old_file), data)
                self._write_dst(op, out_file, patched)
        elif op.type == 10: # BROTLI_BSDIFF
            if old_file and brotli:
                patch_raw = brotli.decompress(data)
                patched = bsdiff4.patch(self._get_source_data(op, old_file), patch_raw)
                self._write_dst(op, out_file, patched)
        elif op.type == 14: # REPLACE_ZSTD
            if zstd:
                dctx = zstd.ZstdDecompressor()
                self._write_dst(op, out_file, dctx.decompress(data))

    def dump_part(self, part):
        total_ops = len(part.operations)
        print(f"[*] Đang trích xuất: {part.partition_name}")
        out_path = os.path.join(self.args.out, f"{part.partition_name}.img")
        
        old_file = None
        if self.args.diff:
            old_path = os.path.join(self.args.old, f"{part.partition_name}.img")
            if os.path.exists(old_path):
                old_file = open(old_path, 'rb')

        try:
            with open(out_path, 'wb') as out_file:
                for i, op in enumerate(part.operations):
                    self.process_op(op, out_file, old_file)
                    # Tính toán phần trăm tiến trình
                    percent = (i + 1) * 100 // total_ops
                    sys.stdout.write(f"\r    Tiến trình: {percent}% [{'#' * (percent // 5)}{'-' * (20 - percent // 5)}] ")
                    sys.stdout.flush()
        finally:
            if old_file: old_file.close()
        print(" -> OK")

    def run(self):
        if not os.path.exists(self.args.out):
            os.makedirs(self.args.out)

        images = self.args.images.split(",") if self.args.images else []
        for part in self.dam.partitions:
            if not images or part.partition_name in images:
                self.dump_part(part)
        print("\n[*] Đã hoàn thành tất cả tác vụ!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Công cụ giải nén Android OTA Payload')
    parser.add_argument('payloadfile', type=argparse.FileType('rb'), help='Đường dẫn file payload.bin')
    parser.add_argument('--out', default='output', help='Thư mục đầu ra')
    parser.add_argument('--diff', action='store_true', help='Chế độ cập nhật Differential')
    parser.add_argument('--old', default='old', help='Thư mục chứa ảnh gốc')
    parser.add_argument('--images', default="", help='Các phân vùng cần lấy (vd: boot,system)')

    args = parser.parse_args()
    try:
        PayloadDumper(args).run()
    except KeyboardInterrupt:
        print("\n[!] Đã dừng bởi người dùng.")
    
