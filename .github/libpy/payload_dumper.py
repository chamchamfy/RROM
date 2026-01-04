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
from google.protobuf.json_format import MessageToJson

def decompress_multi_bz2(data):
    """Giải nén đa luồng BZ2 bằng cách lặp cho đến khi hết dữ liệu."""
    results = []
    while data:
        dec = bz2.BZ2Decompressor()
        try:
            res = dec.decompress(data)
            results.append(res)
            data = dec.unused_data
        except EOFError:
            break
        except Exception:
            break
    return b''.join(results)

def decompress_multi_xz(data):
    """Giải nén đa luồng XZ/LZMA."""
    results = []
    while data:
        dec = lzma.LZMADecompressor(format=lzma.FORMAT_AUTO)
        try:
            res = dec.decompress(data)
            results.append(res)
            data = dec.unused_data
        except EOFError:
            break
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
    sha256 = hashlib.sha256()

    try:
        with open(args_dict['payload_path'], 'rb') as f_pay, open(out_path, 'wb') as f_out:
            for op in part.operations:
                f_pay.seek(data_offset + op.data_offset)
                data = f_pay.read(op.data_length)

                if op.type == um.InstallOperation.REPLACE:
                    out_data = data
                elif op.type == um.InstallOperation.REPLACE_BZ:
                    out_data = decompress_multi_bz2(data)
                elif op.type == um.InstallOperation.REPLACE_XZ:
                    out_data = decompress_multi_xz(data)
                elif op.type == 5: # REPLACE_LZ4
                    out_data = lz4.block.decompress(data, uncompressed_size=op.dst_length)
                elif op.type == 6: # ZERO
                    out_data = b'\x00' * (op.dst_length if op.dst_length else (op.dst_extents[0].num_blocks * block_size))
                elif op.type in [um.InstallOperation.SOURCE_BSDIFF, um.InstallOperation.BROTLI_BSDIFF] and args_dict['diff']:
                    if os.path.exists(old_img_path):
                        with open(old_img_path, 'rb') as f_old:
                            src_io = b''
                            for ext in op.src_extents:
                                f_old.seek(ext.start_block * block_size)
                                src_io += f_old.read(ext.num_blocks * block_size)
                            patch_data = data
                            if op.type == um.InstallOperation.BROTLI_BSDIFF:
                                import brotli
                                patch_data = brotli.decompress(data)
                            out_data = bsdiff4.patch(src_io, patch_data)
                    else:
                        raise FileNotFoundError(f"Thiếu file gốc: {old_img_path}")
                else:
                    out_data = data

                f_out.write(out_data)
                sha256.update(out_data)

        hash_status = ""
        if part.new_partition_info.hash:
            if sha256.digest() != part.new_partition_info.hash:
                hash_status = " | [!] SAI HASH"
        
        sys.stdout.write(f"[OK] {name}.img{hash_status}\n")
        sys.stdout.flush()
        counter.value += 1
        return True

    except Exception as e:
        # Thay thế định dạng thông báo lỗi theo yêu cầu của bạn
        sys.stdout.write(f"[ERROR]: {name}.img | {e}\n")
        sys.stdout.flush()
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
            print("[!] Lỗi: Định dạng file không hợp lệ.")
            sys.exit(1)
        version = struct.unpack('>Q', self.payload_file.read(8))[0]
        manifest_size = struct.unpack('>Q', self.payload_file.read(8))[0]
        sig_size = struct.unpack('>I', self.payload_file.read(4))[0] if version > 1 else 0
        self.manifest_data = self.payload_file.read(manifest_size)
        self.payload_file.read(sig_size)
        self.data_offset = self.payload_file.tell()
        
        self.manifest = update_metadata_pb2.DeltaArchiveManifest()
        self.manifest.ParseFromString(self.manifest_data)

    def run(self):
        if not os.path.exists(self.args.out):
            os.makedirs(self.args.out)
        
        if self.args.metadata:
            meta_file = os.path.join(self.args.out, "metadata.json")
            with open(meta_file, "w", encoding="utf-8") as f:
                f.write(MessageToJson(self.manifest, indent=2))
            print(f"[*] Đã xuất Metadata JSON: {meta_file}")

        if self.args.images or not self.args.metadata:
            work_list = [p for p in self.manifest.partitions if not self.args.images or p.partition_name in self.args.images]
            total = len(work_list)
            print(f"[*] Trích xuất {total} phân vùng với {self.args.threads} luồng xử lý.")
            
            manager = Manager()
            success_counter = manager.Value('i', 0)
            args_dict = {'payload_path': self.args.payload, 'out': self.args.out, 'diff': self.args.diff, 'old': self.args.old}
            tasks = [(p.SerializeToString(), args_dict, self.data_offset, self.manifest.block_size, success_counter) for p in work_list]

            with Pool(processes=self.args.threads) as pool:
                pool.starmap(process_partition, tasks)

            print(f"\nĐã trích xuất thành công: {success_counter.value}/{total} phân vùng.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("payload")
    parser.add_argument("-o", "--out", default="output")
    parser.add_argument("-t", "--threads", type=int, default=2)
    parser.add_argument("-i", "--images", nargs='+')
    parser.add_argument("-m", "--metadata", action="store_true")
    parser.add_argument("--diff", action="store_true")
    parser.add_argument("--old", default="old")
    args = parser.parse_args()
    PayloadDumper(args).run()
                                                  
