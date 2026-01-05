#!/usr/bin/env python3
import os
import sys
import json
import struct
import hashlib
import argparse
import bz2
import lzma
import brotli
import lz4.block
import zstandard as zstd
import bsdiff4
import update_metadata_pb2 as um
from multiprocessing import Pool, Manager

def decompress_xz(data):
    results = []
    while data:
        try:
            dec = lzma.LZMADecompressor(lzma.FORMAT_AUTO)
            results.append(dec.decompress(data))
            data = dec.unused_data
        except lzma.LZMAError:
            break
    return b''.join(results)

def process_partition(part_raw, args, data_offset, block_size, counter):
    p = um.PartitionUpdate()
    p.ParseFromString(part_raw)
    name = p.partition_name
    out_path = os.path.join(args['out'], f"{name}.img")
    
    ops_type = um.InstallOperation
    op_map = {v: k for k, v in ops_type.Type.items()}
    
    if args.get('debug'):
        print(f"[*] Đang trích xuất: {name}...", flush=True)

    try:
        # Khởi tạo file với kích thước chính xác tuyệt đối
        with open(out_path, 'wb') as f:
            f.truncate(p.new_partition_info.size)

        with open(out_path, 'r+b') as f_out, open(args['payload_path'], 'rb') as f_pay:
            for i, op in enumerate(p.operations):
                op_name = op_map.get(op.type, "UNKNOWN")
                
                if args.get('debug'):
                    # In chỉ số i để đối chiếu trực tiếp với metadata của phân vùng đó
                    print(f"  > [{i}] {op_name:<15} | Offset: {op.data_offset:<12} | Size: {op.data_length:<10} bytes", flush=True)

                # Tìm vị trí dữ liệu trong payload.bin
                f_pay.seek(data_offset + op.data_offset)
                data = f_pay.read(op.data_length)
                out_data = b''

                # Logic giải nén dữ liệu
                if op_name in ['ZERO', 'DISCARD']:
                    for ex in op.dst_extents:
                        f_out.seek(ex.start_block * block_size)
                        f_out.write(b'\x00' * (ex.num_blocks * block_size))
                    continue
                elif op_name == 'REPLACE':
                    out_data = data
                elif op_name == 'REPLACE_BZ':
                    out_data = bz2.decompress(data)
                elif op_name == 'REPLACE_XZ':
                    out_data = decompress_xz(data)
                elif op_name == 'REPLACE_LZ4':
                    out_data = lz4.block.decompress(data, uncompressed_size=op.dst_length)
                elif op_name == 'REPLACE_ZSTD':
                    out_data = zstd.ZstdDecompressor().decompress(data, max_output_size=op.dst_length)
                elif op_name == 'REPLACE_BROTLI':
                    out_data = brotli.decompress(data)
                elif op_name in ['SOURCE_COPY', 'SOURCE_BSDIFF', 'BROTLI_BSDIFF', 'BSDIFF', 
                                 'PUFFDIFF', 'ZUCCHINI', 'LZ4DIFF_BSDIFF', 'LZ4DIFF_PUFFDIFF']:
                    if not args['diff']:
                        raise Exception(f"Cần --diff cho {op_name}")
                    old_path = os.path.join(args['old'], f"{name}.img")
                    if not os.path.exists(old_path):
                        raise Exception(f"Thiếu file gốc: {old_path}")
                    with open(old_path, 'rb') as f_old:
                        src = b''.join((f_old.seek(e.start_block * block_size) or f_old.read(e.num_blocks * block_size)) for e in op.src_extents)
                    
                    if op_name == 'SOURCE_COPY':
                        out_data = src
                    else:
                        patch_data = data if op_name != 'BROTLI_BSDIFF' else brotli.decompress(data)
                        out_data = bsdiff4.patch(src, patch_data)
                else:
                    out_data = data

                # Ghi dữ liệu ra file đầu ra theo đúng extents
                ptr = 0
                for ex in op.dst_extents:
                    f_out.seek(ex.start_block * block_size)
                    sz = ex.num_blocks * block_size
                    # Cắt đúng đoạn dữ liệu tương ứng với từng extent
                    f_out.write(out_data[ptr : ptr + sz])
                    ptr += sz

        # Kiểm tra HASH
        with open(out_path, 'rb') as f:
            actual_h = hashlib.sha256(f.read()).hexdigest()
        expect_h = p.new_partition_info.hash.hex()
        
        status = ""
        if expect_h and actual_h != expect_h:
            status = f" | Lỗi: Sai HASH (tính toán: {actual_h}, đúng: {expect_h})"
            
        if not args.get('debug') or status:
            print(f"[OK] {name}.img{status}", flush=True)
        counter.value += 1
    except Exception as e:
        print(f"[ERROR] {name} Lỗi tại Op {i} ({op_name}): {e}", flush=True)

class PayloadDumper:
    def __init__(self, args):
        self.args = args
        if not os.path.exists(args.payload):
            sys.exit(f"Lỗi: Không tìm thấy file {args.payload}")
        
        try:
            with open(args.payload, 'rb') as f:
                if f.read(4) != b'CrAU': 
                    sys.exit("Lỗi: payload.bin không hợp lệ (Magic 'CrAU' không khớp)")
                self.ver, self.m_size = struct.unpack('>QQ', f.read(16))
                self.sig_size = struct.unpack('>I', f.read(4))[0] if self.ver > 1 else 0
                self.m_data = f.read(self.m_size)
                self.data_offset = f.tell() + self.sig_size
            self.manifest = um.DeltaArchiveManifest()
            self.manifest.ParseFromString(self.m_data)
        except Exception as e:
            sys.exit(f"Lỗi đọc file payload: {e}")

    def run(self):
        os.makedirs(self.args.out, exist_ok=True)
        if self.args.metadata:
            m = self.manifest
            groups = [{"group_name": g.name, "size": g.size, "partitions": list(g.partition_names)} for g in m.dynamic_partition_metadata.groups] if m.dynamic_partition_metadata else []
            parts = [{"partition_name": p.partition_name, "size_bytes": p.new_partition_info.size, "sha256_hash": p.new_partition_info.hash.hex() if p.new_partition_info.hash else "N/A"} for p in m.partitions]
            out_path = os.path.abspath(os.path.join(self.args.out, "metadata.json"))
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump({"block_size": m.block_size, "super_groups": groups, "all_partitions": parts}, f, indent=2, ensure_ascii=False)
            return print(f"[*] Đã xuất metadata.json vào {out_path}")

        if self.args.list:
            print(f"{'Phân vùng':<25} | {'Kích thước':<15} | {'Hash'}")
            for p in self.manifest.partitions:
                h = p.new_partition_info.hash.hex()[:10] + "..." if p.new_partition_info.hash else "N/A"
                print(f"{p.partition_name:<25} | {p.new_partition_info.size:<15} | {h}")
            return

        work = [p for p in self.manifest.partitions if not self.args.images or p.partition_name in self.args.images]
        threads = 1 if self.args.debug else self.args.threads
        print(f"[*] Đang trích xuất {len(work)} phân vùng với {threads} luồng xử lý...")
        
        counter = Manager().Value('i', 0)
        with Pool(threads) as pool:
            pool.starmap(process_partition, [(p.SerializeToString(), vars(self.args), self.data_offset, self.manifest.block_size, counter) for p in work])
        print(f"[*] Hoàn tất {counter.value}/{len(work)} phân vùng.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Payload Dumper CC")
    parser.add_argument("payload", help="Đường dẫn đến file payload.bin")
    parser.add_argument("-o", "--out", default="output", help="Thư mục xuất (mặc định: output)")
    parser.add_argument("-t", "--threads", type=int, default=1, help="Số lượng luồng xử lý đồng thời (mặc định: 1)")
    parser.add_argument("-i", "--images", nargs='+', help="Chỉ trích xuất các phân vùng cụ thể (ví dụ: boot system)")
    parser.add_argument("-l", "--list", action="store_true", help="Liệt kê danh sách các phân vùng")
    parser.add_argument("-m", "--metadata", action="store_true", help="Xuất thông tin cấu trúc phân vùng ra file metadata.json")
    parser.add_argument("-d", "--debug", action="store_true", default=True, help="Bật chế độ Debug")
    parser.add_argument("--diff", action="store_true", help="Sử dụng (--diff) chế độ Delta OTA (yêu cầu phân vùng gốc)")
    parser.add_argument("--old", default="old", help="Thư mục chứa các file .img gốc cho chế độ Delta khi sử dụng --diff (mặc định: old)")
    
    args = parser.parse_args()
    setattr(args, 'payload_path', args.payload)
    if len(sys.argv) == 1: parser.print_help()
    else: PayloadDumper(args).run()
