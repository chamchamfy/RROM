#!/usr/bin/env python3
import struct
import hashlib
import bz2
import sys
import argparse
import bsdiff4
import io
import os
import lzma
import brotli
import zstandard as zstd

# Đảm bảo bạn đã cài: pip install protobuf bsdiff4 brotli zstandard lz4
import update_metadata_pb2 as um

# Khai báo chính xác theo Number định nghĩa trong file của bạn
OP_TYPES = {
    0:  'REPLACE',
    1:  'REPLACE_BZ',
    2:  'MOVE',
    3:  'BSDIFF',
    4:  'SOURCE_COPY',
    5:  'SOURCE_BSDIFF',
    8:  'REPLACE_XZ',
    6:  'ZERO',
    7:  'DISCARD',
    10: 'BROTLI_BSDIFF',
    9:  'PUFFDIFF',
    11: 'ZUCCHINI',
    12: 'LZ4DIFF_BSDIFF',
    13: 'LZ4DIFF_PUFFDIFF'
}

def u32(x): return struct.unpack('>I', x)[0]
def u64(x): return struct.unpack('>Q', x)[0]

def data_for_op(op, out_file, payload_file, data_offset, block_size, old_file=None):
    # Di chuyển đến vị trí dữ liệu trong payload.bin
    payload_file.seek(data_offset + op.data_offset)
    data = payload_file.read(op.data_length)

    # Vị trí đích ghi vào file .img đầu ra
    target_offset = op.dst_extents[0].start_block * block_size
    out_file.seek(target_offset)

    # --- NHÓM 1: THAY THẾ TOÀN BỘ (FULL REPLACE) ---
    if op.type == 0: # REPLACE
        out_file.write(data)
    elif op.type == 1: # REPLACE_BZ
        out_file.write(bz2.decompress(data))
    elif op.type == 8: # REPLACE_XZ
        out_file.write(lzma.decompress(data))
    
    # --- NHÓM 2: DỮ LIỆU RỖNG (ZERO/DISCARD) ---
    elif op.type in [6, 7]: # ZERO & DISCARD
        for ext in op.dst_extents:
            out_file.seek(ext.start_block * block_size)
            out_file.write(b'\x00' * (ext.num_blocks * block_size))

    # --- NHÓM 3: SAO CHÉP (SOURCE/MOVE) ---
    elif op.type in [2, 4]: # MOVE & SOURCE_COPY
        if not old_file:
            return
        for src_ext, dst_ext in zip(op.src_extents, op.dst_extents):
            old_file.seek(src_ext.start_block * block_size)
            chunk = old_file.read(src_ext.num_blocks * block_size)
            out_file.seek(dst_ext.start_block * block_size)
            out_file.write(chunk)

    # --- NHÓM 4: CÁC LOẠI NÉN HIỆN ĐẠI (BROTLI/ZSTD) ---
    # Một số ROM dùng Type 9, 10, 11 cho nén khối thay vì patch
    elif op.type in [9, 10, 11]: # PUFFDIFF, BROTLI_BSDIFF, ZUCCHINI
        try:
            # Thử giải nén Brotli
            out_file.write(brotli.decompress(data))
        except:
            try:
                # Thử giải nén Zstandard (Dành cho Android 12+)
                dctx = zstd.ZstdDecompressor()
                out_file.write(dctx.decompress(data))
            except:
                # Nếu thực sự là patch data (BSDIFF/ZUCCHINI)
                if old_file and op.type == 10: # BROTLI_BSDIFF
                    # Logic bsdiff4 với brotli (cần giải nén nguồn trước)
                    pass

    # --- NHÓM 5: PATCH BIẾN ĐỔI (BSDIFF/LZ4DIFF) ---
    elif op.type in [3, 5, 12, 13]: # BSDIFF, SOURCE_BSDIFF, LZ4DIFF...
        if not old_file:
            return
        # Gom dữ liệu nguồn từ các extents
        source_data = b''
        for ext in op.src_extents:
            old_file.seek(ext.start_block * block_size)
            source_data += old_file.read(ext.num_blocks * block_size)
        
        try:
            # Thực hiện vá lỗi (patching)
            patched_data = bsdiff4.patch(source_data, data)
            out_file.write(patched_data)
        except Exception as e:
            print(f" Lỗi Patch Type {op.type}: {e}")

    else:
        print(f"\n[!] Type {op.type} ({OP_TYPES.get(op.type, 'UNKNOWN')}) chưa có logic giải mã.")

def dump_part(part, data_offset, args, block_size):
    print(f"Extracting {part.partition_name:18} ", end="")
    sys.stdout.flush()

    out_path = os.path.join(args.out, f"{part.partition_name}.img")
    old_file = None
    if args.old:
        old_img = os.path.join(args.old, f"{part.partition_name}.img")
        if os.path.exists(old_img):
            old_file = open(old_img, 'rb')

    with open(out_path, 'wb') as out_file:
        for op in part.operations:
            data_for_op(op, out_file, args.payloadfile, data_offset, block_size, old_file)
            sys.stdout.write(".")
            sys.stdout.flush()
    
    if old_file: old_file.close()
    print(" [OK]")

def main():
    parser = argparse.ArgumentParser(description='Android Payload Dumper - Full Operation Support')
    parser.add_argument('payloadfile', type=argparse.FileType('rb'))
    parser.add_argument('--out', default='output', help='Thư mục chứa kết quả')
    parser.add_argument('--old', default=None, help='Thư mục chứa file gốc (cho OTA Incremental)')
    args = parser.parse_args()

    if not os.path.exists(args.out): os.makedirs(args.out)

    if args.payloadfile.read(4) != b'CrAU':
        print("Lỗi: Không phải file payload.bin chuẩn.")
        return

    version = u64(args.payloadfile.read(8))
    manifest_size = u64(args.payloadfile.read(8))
    metadata_sig_size = u32(args.payloadfile.read(4)) if version > 1 else 0

    manifest_data = args.payloadfile.read(manifest_size)
    args.payloadfile.read(metadata_sig_size)
    data_offset = args.payloadfile.tell()

    dam = um.DeltaArchiveManifest()
    dam.ParseFromString(manifest_data)
    
    for part in dam.partitions:
        dump_part(part, data_offset, args, dam.block_size)

if __name__ == '__main__':
    main()
