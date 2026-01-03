#!/usr/bin/env python3
import os
import argparse
import struct
import bz2
import lzma
import json
import lz4.block
import zstandard as zstd
import bsdiff4
import update_metadata_pb2
from multiprocessing import Pool
from google.protobuf.json_format import MessageToJson

class PayloadDumper:
    def __init__(self, payload_path, out_dir, thread_count, select_images, dump_meta, diff_mode, old_dir):
        self.payload_path = payload_path
        self.out_dir = out_dir
        self.thread_count = thread_count
        self.select_images = select_images
        self.dump_meta = dump_meta
        self.diff_mode = diff_mode
        self.old_dir = old_dir
        self.data_offset = 0
        self.manifest = None

        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

    def _parse_manifest(self):
        try:
            with open(self.payload_path, 'rb') as f:
                magic = f.read(4)
                if magic != b'CrOS':
                    raise ValueError("Không phải file payload.bin hợp lệ!")

                file_format_version = struct.unpack('>Q', f.read(8))[0]
                manifest_size = struct.unpack('>Q', f.read(8))[0]
                metadata_sig_size = 0
                if file_format_version > 1:
                    metadata_sig_size = struct.unpack('>I', f.read(4))[0]

                manifest_data = f.read(manifest_size)
                self.manifest = update_metadata_pb2.DeltaArchiveManifest()
                self.manifest.ParseFromString(manifest_data)
                self.data_offset = f.tell() + metadata_sig_size

            if self.dump_meta:
                json_data = MessageToJson(self.manifest)
                with open(os.path.join(self.out_dir, "metadata.json"), "w", encoding="utf-8") as jf:
                    jf.write(json_data)
                print(f"[+] Metadata đã xuất: {self.out_dir}/metadata.json")
        except Exception as e:
            print(f"[!] Lỗi Payload: {e}")
            exit(1)

    def _get_data_from_extents(self, f, extents, block_size):
        data = b''
        for extent in extents:
            f.seek(extent.start_block * block_size)
            data += f.read(extent.num_blocks * block_size)
        return data

    def _extract_partition(self, partition):
        name = partition.partition_name
        if self.select_images and name not in self.select_images:
            return

        output_path = os.path.join(self.out_dir, f"{name}.img")
        old_img_path = os.path.join(self.old_dir, f"{name}.img")
        dctx = zstd.ZstdDecompressor()
        block_size = self.manifest.block_size or 4096

        try:
            with open(self.payload_path, 'rb') as f_pay, open(output_path, 'wb') as f_out:
                for op in partition.operations:
                    f_pay.seek(self.data_offset + op.data_offset)
                    data = f_pay.read(op.data_length)

                    # --- NHÓM 1: CÁC THAO TÁC REPLACE (FULL) ---
                    if op.type == update_metadata_pb2.InstallOperation.REPLACE:
                        f_out.write(data)
                    elif op.type == update_metadata_pb2.InstallOperation.REPLACE_BZ:
                        f_out.write(bz2.decompress(data))
                    elif op.type == update_metadata_pb2.InstallOperation.REPLACE_XZ:
                        f_out.write(lzma.decompress(data))
                    elif op.type == 5: # REPLACE_LZ4
                        f_out.write(lz4.block.decompress(data, uncompressed_size=op.dst_length))
                    elif op.type == 6: # REPLACE_ZSTD
                        f_out.write(dctx.decompress(data, max_output_size=op.dst_length))

                    # --- NHÓM 2: CÁC THAO TÁC DIFFERENTIAL (DELTA) ---
                    elif op.type in [update_metadata_pb2.InstallOperation.SOURCE_BSDIFF, 
                                   update_metadata_pb2.InstallOperation.BROTLI_BSDIFF]:
                        if not self.diff_mode:
                            raise Exception("Phát hiện gói Delta. Vui lòng thêm flag --diff và --old")
                        
                        with open(old_img_path, 'rb') as f_old:
                            old_data = self._get_data_from_extents(f_old, op.src_extents, block_size)
                            f_out.write(bsdiff4.patch(old_data, data))
                            
                    elif op.type == update_metadata_pb2.InstallOperation.SOURCE_COPY:
                        if not self.diff_mode:
                            raise Exception("Phát hiện gói Delta. Vui lòng thêm flag --diff và --old")
                        with open(old_img_path, 'rb') as f_old:
                            f_out.write(self._get_data_from_extents(f_old, op.src_extents, block_size))

            print(f"[OK] {name}.img")
        except Exception as e:
            print(f"[ERROR] {name}.img | Lỗi: {e}")

    def run(self):
        self._parse_manifest()
        work_list = [p for p in self.manifest.partitions if not self.select_images or p.partition_name in self.select_images]
        
        print(f"[*] Đang xử lý {len(work_list)} phân vùng với {self.thread_count} luồng.")
        if self.diff_mode:
            print(f"[*] Chế độ Differential: BẬT (Thư mục cũ: {self.old_dir})")

        with Pool(processes=self.thread_count) as pool:
            pool.map(self._extract_partition, work_list)
        print("\n[--- HOÀN TẤT ---]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Android Payload Dumper Pro (Full & Delta Support)")
    parser.add_argument("payload", help="Đường dẫn đến file payload.bin")
    parser.add_argument("-o", "--out", default="output", help="Thư mục đầu ra (Mặc định: output)")
    parser.add_argument("-t", "--threads", type=int, default=1, help="Số lượng luồng (Mặc định: 1)")
    parser.add_argument("-i", "--images", nargs='+', help="Chỉ trích xuất các phân vùng cụ thể")
    parser.add_argument("-m", "--metadata", action="store_true", help="Xuất metadata.json")
    parser.add_argument("--diff", action="store_true", help="Trích xuất OTA differential (cần thư mục old)")
    parser.add_argument("--old", default="old", help="Thư mục chứa file cũ (mặc định: old)")

    args = parser.parse_args()

    dumper = PayloadDumper(args.payload, args.out, args.threads, args.images, args.metadata, args.diff, args.old)
    dumper.run()