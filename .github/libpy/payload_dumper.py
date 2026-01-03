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
try:
    import brotli
except ImportError:
    print("Lỗi: Vui lòng cài đặt thư viện brotli: pip install brotli")
    sys.exit(1)
try:
    import lz4.block
except ImportError:
    print("Lỗi: Vui lòng cài đặt thư viện lz4: pip install lz4")
    sys.exit(1)

import update_metadata_pb2 as um

def u32(x):
    return struct.unpack('>I', x)[0]

def u64(x):
    return struct.unpack('>Q', x)[0]

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

def apply_bsdiff(old_data, patch):
    return bsdiff4.patch(old_data, patch)

def apply_puffdiff(old_data, patch):
    raise NotImplementedError("Puffdiff chưa được hỗ trợ")

def apply_zucchini(old_data, patch):
    raise NotImplementedError("Zucchini chưa được hỗ trợ")

def data_for_op(op, payload_file, out_file, old_file, data_offset, block_size):
    payload_file.seek(data_offset + op.data_offset)
    data = payload_file.read(op.data_length)

    if op.data_sha256_hash:
        assert hashlib.sha256(data).digest() == op.data_sha256_hash, "Lỗi: Dữ liệu không khớp với hash"

    if op.type == op.REPLACE:
        write_extents(out_file, op.dst_extents, data, block_size)
    elif op.type == op.REPLACE_BZ:
        data = bz2.decompress(data)
        write_extents(out_file, op.dst_extents, data, block_size)
    elif op.type == op.REPLACE_XZ:
        data = lzma.decompress(data)
        write_extents(out_file, op.dst_extents, data, block_size)
    elif op.type == op.SOURCE_COPY:
        if not old_file:
            raise ValueError("SOURCE_COPY chỉ hỗ trợ cho OTA differential")
        old_data = read_extents(old_file, op.src_extents, block_size)
        write_extents(out_file, op.dst_extents, old_data, block_size)
    elif op.type == op.SOURCE_BSDIFF:
        if not old_file:
            raise ValueError("SOURCE_BSDIFF chỉ hỗ trợ cho OTA differential")
        old_data = read_extents(old_file, op.src_extents, block_size)
        patched = apply_bsdiff(old_data, data)
        write_extents(out_file, op.dst_extents, patched, block_size)
    elif op.type == op.BROTLI_BSDIFF:
        if not old_file:
            raise ValueError("BROTLI_BSDIFF chỉ hỗ trợ cho OTA differential")
        old_data = read_extents(old_file, op.src_extents, block_size)
        data = brotli.decompress(data)
        patched = apply_bsdiff(old_data, data)
        write_extents(out_file, op.dst_extents, patched, block_size)
    elif op.type == op.PUFFDIFF:
        if not old_file:
            raise ValueError("PUFFDIFF chỉ hỗ trợ cho OTA differential")
        old_data = read_extents(old_file, op.src_extents, block_size)
        patched = apply_puffdiff(old_data, data)
        write_extents(out_file, op.dst_extents, patched, block_size)
    elif op.type == op.ZUCCHINI:
        if not old_file:
            raise ValueError("ZUCCHINI chỉ hỗ trợ cho OTA differential")
        old_data = read_extents(old_file, op.src_extents, block_size)
        patched = apply_zucchini(old_data, data)
        write_extents(out_file, op.dst_extents, patched, block_size)
    elif op.type == op.LZ4DIFF_BSDIFF:
        if not old_file:
            raise ValueError("LZ4DIFF_BSDIFF chỉ hỗ trợ cho OTA differential")
        old_data = read_extents(old_file, op.src_extents, block_size)
        data = lz4.block.decompress(data)
        patched = apply_bsdiff(old_data, data)
        write_extents(out_file, op.dst_extents, patched, block_size)
    elif op.type == op.LZ4DIFF_PUFFDIFF:
        if not old_file:
            raise ValueError("LZ4DIFF_PUFFDIFF chỉ hỗ trợ cho OTA differential")
        old_data = read_extents(old_file, op.src_extents, block_size)
        data = lz4.block.decompress(data)
        patched = apply_puffdiff(old_data, data)
        write_extents(out_file, op.dst_extents, patched, block_size)
    elif op.type == op.MOVE:
        if not old_file:
            raise ValueError("MOVE chỉ hỗ trợ cho OTA differential")
        old_data = read_extents(old_file, op.src_extents, block_size)
        write_extents(out_file, op.dst_extents, old_data, block_size)
    elif op.type == op.ZERO:
        for ext in op.dst_extents:
            out_file.seek(ext.start_block * block_size)
            out_file.write(b'\x00' * ext.num_blocks * block_size)
    elif op.type == op.DISCARD:
        pass
    else:
        raise ValueError(f"Lỗi: Loại operation không được hỗ trợ: {op.type}")

def cow_merge_op(op, old_file, out_file, block_size):
    if op.type == op.COW_COPY:
        old_data = read_extents(old_file, [op.src_extent], block_size)
        write_extents(out_file, [op.dst_extent], old_data, block_size)
    elif op.type == op.COW_XOR:
        raise NotImplementedError("COW_XOR chưa được hỗ trợ")
    elif op.type == op.COW_REPLACE:
        raise NotImplementedError("COW_REPLACE chưa được hỗ trợ")
    else:
        raise ValueError(f"Lỗi: Loại COW operation không được hỗ trợ: {op.type}")

def dump_partition(part, payload_file, out_dir, old_dir, data_offset, block_size, is_diff):
    old_file = None
    if is_diff:
        old_path = os.path.join(old_dir, f"{part.partition_name}.img")
        if not os.path.exists(old_path):
            raise FileNotFoundError(f"Lỗi: Không tìm thấy file cũ: {old_path}")
        old_file = open(old_path, 'rb')

    out_path = os.path.join(out_dir, f"{part.partition_name}.img")
    out_file = open(out_path, 'wb')

    for op in part.operations:
        data_for_op(op, payload_file, out_file, old_file, data_offset, block_size)

    for merge_op in part.merge_operations:
        cow_merge_op(merge_op, old_file, out_file, block_size)

    if old_file:
        old_file.close()
    out_file.close()
    return part.partition_name

def dump_metadata(dam, out_dir):
    metadata = {
        "block_size": dam.block_size,
        "partitions": [
            {
                "name": part.partition_name,
                "operations": len(part.operations),
                "merge_operations": len(part.merge_operations),
                "size": part.new_partition_info.size if part.new_partition_info else 0,
                "hash": part.new_partition_info.hash.hex() if part.new_partition_info else None,
            }
            for part in dam.partitions
        ],
        "dynamic_partition_metadata": {
            "groups": [
                {
                    "name": group.name,
                    "size": group.size,
                    "partition_names": group.partition_names,
                }
                for group in dam.dynamic_partition_metadata.groups
            ]
            if dam.dynamic_partition_metadata else None,
        },
        "apex_info": [
            {
                "package_name": apex.package_name,
                "version": apex.version,
                "is_compressed": apex.is_compressed,
                "decompressed_size": apex.decompressed_size,
            }
            for apex in dam.apex_info
        ]
        if dam.apex_info else None,
    }
    metadata_path = os.path.join(out_dir, "metadata.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"Đã lưu metadata vào: {metadata_path}")

def main():
    parser = argparse.ArgumentParser(description="Công cụ trích xuất payload.bin (OTA)")
    parser.add_argument("payload", type=argparse.FileType('rb'), help="File payload.bin")
    parser.add_argument("-o", "--out", default="output", help="Thư mục đầu ra (mặc định: output)")
    parser.add_argument("-t", "--threads", type=int, default=1, help="Số luồng xử lý (mặc định: 1)")
    parser.add_argument("-m", "--metadata", action="store_true", help="Xuất metadata ra file JSON")
    parser.add_argument("--diff", action="store_true", help="Trích xuất OTA differential (cần thư mục old)")
    parser.add_argument("--old", default="old", help="Thư mục chứa file cũ (mặc định: old)")
    parser.add_argument("-i", "--images", default="", help="Danh sách partition cần trích xuất, cách nhau bằng dấu phẩy")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    magic = args.payload.read(4)
    assert magic == b'CrAU', "Lỗi: File payload không hợp lệ (sai magic)"

    file_format_version = u64(args.payload.read(8))
    assert file_format_version == 2, "Lỗi: Phiên bản file không được hỗ trợ"

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

    if args.images:
        images = args.images.split(",")
        partitions = [part for part in dam.partitions if part.partition_name in images]
        if not partitions:
            print("Cảnh báo: Không tìm thấy partition nào trong danh sách!")
    else:
        partitions = dam.partitions

    print(f"Bắt đầu trích xuất {len(partitions)} partition(s) với {args.threads} luồng...")

    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = []
        for part in partitions:
            future = executor.submit(
                dump_partition,
                part, args.payload, args.out, args.old, data_offset, block_size, args.diff
            )
            futures.append(future)

        for future in as_completed(futures):
            partition_name = future.result()
            print(f"Đã trích xuất: {partition_name}")

    print("Hoàn tất!")

if __name__ == "__main__":
    main()
