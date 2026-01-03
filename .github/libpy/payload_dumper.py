#!/usr/bin/env python3
import os
import sys
import struct
import hashlib
import bz2
import argparse
import bsdiff4
import io
import json
import lzma
from concurrent.futures import ThreadPoolExecutor, as_completed

# Cài đặt thư viện cần thiết
try:
    import brotli
except ImportError:
    print("Lỗi: Vui lòng cài đặt brotli: pip install brotli")
    sys.exit(1)
try:
    import lz4.block
except ImportError:
    print("Lỗi: Vui lòng cài đặt lz4: pip install lz4")
    sys.exit(1)
try:
    import zstandard as zstd
except ImportError:
    print("Lỗi: Vui lòng cài đặt zstandard: pip install zstandard")
    sys.exit(1)

import update_metadata_pb2 as um

def u32(data):
    return struct.unpack('>I', data)[0]

def u64(data):
    return struct.unpack('>Q', data)[0]

def read_extents(file, extents, block_size):
    data = b''
    for ext in extents:
        file.seek(ext.start_block * block_size)
        data += file.read(ext.num_blocks * block_size)
    return data

def write_extents(out_file, extents, data, block_size):
    pos = 0
    for ext in extents:
        out_file.seek(ext.start_block * block_size)
        out_file.write(data[pos:pos + ext.num_blocks * block_size])
        pos += ext.num_blocks * block_size

def decompress_xz(data):
    try:
        return lzma.decompress(data)
    except Exception as e:
        print(f"[!] Lỗi giải nén XZ: {str(e)}")
        return None

def decompress_bz2(data):
    try:
        return bz2.decompress(data)
    except Exception as e:
        print(f"[!] Lỗi giải nén BZ2: {str(e)}")
        return None

def decompress_zstd(data):
    try:
        return zstd.ZstdDecompressor().decompress(data)
    except Exception as e:
        print(f"[!] Lỗi giải nén ZSTD: {str(e)}")
        return None

def decompress_brotli(data):
    try:
        return brotli.decompress(data)
    except Exception as e:
        print(f"[!] Lỗi giải nén Brotli: {str(e)}")
        return None

def decompress_lz4(data):
    try:
        return lz4.block.decompress(data)
    except Exception as e:
        print(f"[!] Lỗi giải nén LZ4: {str(e)}")
        return None

def try_decompress(data):
    # Ưu tiên XZ và BZ2 trước
    decompressors = [
        ("XZ", decompress_xz),
        ("BZ2", decompress_bz2),
        ("ZSTD", decompress_zstd),
        ("Brotli", decompress_brotli),
        ("LZ4", decompress_lz4),
    ]
    for name, func in decompressors:
        result = func(data)
        if result is not None:
            print(f"[+] Giải nén thành công bằng {name}")
            return result
    print("[!] Không thể giải nén, sử dụng dữ liệu gốc")
    return data

def apply_bsdiff(old_data, patch):
    return bsdiff4.patch(old_data, patch)

def data_for_op(op, payload_file, out_file, old_file, data_offset, block_size, partition_name):
    payload_file.seek(data_offset + op.data_offset)
    data = payload_file.read(op.data_length)

    if op.data_sha256_hash:
        current_hash = hashlib.sha256(data).digest()
        if current_hash != op.data_sha256_hash:
            print(f"[!] Cảnh báo: Hash không khớp cho {partition_name} ({op.type})")

    try:
        if op.type == um.InstallOperation.REPLACE:
            write_extents(out_file, op.dst_extents, data, block_size)
        elif op.type == um.InstallOperation.REPLACE_ZSTD:
            data = try_decompress(data)
            write_extents(out_file, op.dst_extents, data, block_size)
        elif op.type == um.InstallOperation.REPLACE_BZ:
            data = decompress_bz2(data)
            if data is None:
                data = try_decompress(data)
            write_extents(out_file, op.dst_extents, data, block_size)
        elif op.type == um.InstallOperation.REPLACE_XZ:
            data = decompress_xz(data)
            if data is None:
                data = try_decompress(data)
            write_extents(out_file, op.dst_extents, data, block_size)
        elif op.type == um.InstallOperation.SOURCE_COPY:
            if not old_file:
                raise ValueError(f"SOURCE_COPY yêu cầu file cũ cho {partition_name}")
            old_data = read_extents(old_file, op.src_extents, block_size)
            write_extents(out_file, op.dst_extents, old_data, block_size)
        elif op.type in [um.InstallOperation.SOURCE_BSDIFF, um.InstallOperation.BROTLI_BSDIFF, um.InstallOperation.ZSTD_BSDIFF, um.InstallOperation.LZ4DIFF_BSDIFF]:
            if not old_file:
                raise ValueError(f"{op.type} yêu cầu file cũ cho {partition_name}")
            old_data = read_extents(old_file, op.src_extents, block_size)
            data = try_decompress(data)
            patched = apply_bsdiff(old_data, data)
            write_extents(out_file, op.dst_extents, patched, block_size)
        elif op.type == um.InstallOperation.MOVE:
            if not old_file:
                raise ValueError(f"MOVE yêu cầu file cũ cho {partition_name}")
            old_data = read_extents(old_file, op.src_extents, block_size)
            write_extents(out_file, op.dst_extents, old_data, block_size)
        elif op.type == um.InstallOperation.ZERO:
            for ext in op.dst_extents:
                out_file.seek(ext.start_block * block_size)
                out_file.write(b'\x00' * ext.num_blocks * block_size)
        elif op.type == um.InstallOperation.DISCARD:
            pass
        else:
            print(f"[!] Cảnh báo: Loại operation không được hỗ trợ: {partition_name} ({op.type})")
            data = try_decompress(data)
            if old_file and op.src_extents:
                old_data = read_extents(old_file, op.src_extents, block_size)
                patched = apply_bsdiff(old_data, data)
                write_extents(out_file, op.dst_extents, patched, block_size)
            else:
                write_extents(out_file, op.dst_extents, data, block_size)
    except Exception as e:
        print(f"[!] Lỗi khi xử lý {partition_name} ({op.type}): {str(e)}")
        raise

def dump_partition(part, payload_file, out_dir, old_dir, data_offset, block_size, is_diff):
    partition_name = part.partition_name
    old_file = None
    if is_diff:
        old_path = os.path.join(old_dir, f"{partition_name}.img")
        if not os.path.exists(old_path):
            print(f"[!] Lỗi: Không tìm thấy file cũ: {old_path}")
            return None
        old_file = open(old_path, 'rb')

    out_path = os.path.join(out_dir, f"{partition_name}.img")
    out_file = open(out_path, 'wb')

    try:
        for op in part.operations:
            data_for_op(op, payload_file, out_file, old_file, data_offset, block_size, partition_name)
        print(f"[+] Hoàn tất: {partition_name}")
    except Exception as e:
        print(f"[!] Lỗi khi trích xuất {partition_name}: {str(e)}")
        out_file.close()
        if old_file:
            old_file.close()
        os.remove(out_path)
        return None

    out_file.close()
    if old_file:
        old_file.close()
    return partition_name

def dump_metadata(dam, out_dir):
    metadata = {
        "block_size": dam.block_size,
        "partitions": [
            {
                "name": part.partition_name,
                "operations": len(part.operations),
                "size": part.new_partition_info.size if part.new_partition_info else 0,
                "hash": part.new_partition_info.hash.hex() if part.new_partition_info and part.new_partition_info.hash else None,
            }
            for part in dam.partitions
        ],
    }
    metadata_path = os.path.join(out_dir, "metadata.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"[+] Đã lưu metadata: {metadata_path}")

def main():
    parser = argparse.ArgumentParser(description="Công cụ trích xuất payload.bin (OTA)")
    parser.add_argument("payload", type=argparse.FileType('rb'), help="File payload.bin")
    parser.add_argument("-o", "--out", default="output", help="Thư mục đầu ra (mặc định: output)")
    parser.add_argument("-t", "--threads", type=int, default=1, help="Số luồng xử lý (mặc định: 1)")
    parser.add_argument("-m", "--metadata", action="store_true", help="Xuất metadata ra JSON")
    parser.add_argument("--diff", action="store_true", help="Trích xuất OTA differential (cần thư mục old)")
    parser.add_argument("--old", default="old", help="Thư mục chứa file cũ (mặc định: old)")
    parser.add_argument("-i", "--images", default="", help="Danh sách partition (ví dụ: system,boot,vendor)")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    # Đọc header payload
    magic = args.payload.read(4)
    if magic != b'CrAU':
        print("Lỗi: File payload không hợp lệ (sai magic)")
        sys.exit(1)

    file_format_version = u64(args.payload.read(8))
    if file_format_version != 2:
        print("Lỗi: Phiên bản file không được hỗ trợ")
        sys.exit(1)

    manifest_size = u64(args.payload.read(8))
    metadata_signature_size = u32(args.payload.read(4)) if file_format_version > 1 else 0
    manifest = args.payload.read(manifest_size)
    args.payload.read(metadata_signature_size)

    data_offset = args.payload.tell()
    dam = um.DeltaArchiveManifest()
    dam.ParseFromString(manifest)
    block_size = dam.block_size

    if args.metadata:
        dump_metadata(dam, args.out)

    # Lọc partition nếu có danh sách
    if args.images:
        images = args.images.split(",")
        partitions = [p for p in dam.partitions if p.partition_name in images]
        if not partitions:
            print("Lỗi: Không tìm thấy partition nào trong danh sách!")
            sys.exit(1)
    else:
        partitions = dam.partitions

    print(f"[*] Bắt đầu trích xuất {len(partitions)} partition(s) với {args.threads} luồng...")

    # Trích xuất đa luồng (nếu threads > 1)
    if args.threads > 1:
        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = []
            for part in partitions:
                future = executor.submit(
                    dump_partition,
                    part, args.payload, args.out, args.old, data_offset, block_size, args.diff
                )
                futures.append(future)

            success = 0
            for future in as_completed(futures):
                if future.result():
                    success += 1
    else:
        # Chạy tuần tự nếu threads = 1
        success = 0
        for part in partitions:
            result = dump_partition(part, args.payload, args.out, args.old, data_offset, block_size, args.diff)
            if result:
                success += 1

    print(f"[+] Hoàn tất! Trích xuất thành công {success}/{len(partitions)} partition(s).")

if __name__ == "__main__":
    main()
