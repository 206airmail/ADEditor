"""
DDSReader - Native DDS file reader in Python
Based on DDSReader.java (MIT License) by Kenji Sasaki
https://github.com/npedotnet/DDSReader

Improvements by KillBait: https://github.com/KillBait/AutoDrive_Course_Editor
Ported to Python for ADEditor

This module provides a pure Python implementation for reading DirectDraw Surface (DDS)
files and converting them to wxPython images, with no external dependencies beyond
numpy and wxPython.
"""

import struct
import time
import numpy as np
import wx
from typing import Tuple, Optional


class DDSReader:
    """Native DDS file decoder supporting common formats used in Farming Simulator"""
    
    # DDS Format Type Constants
    DXT1 = 0x44585431  # 'DXT1' in big-endian
    DXT2 = 0x44585432
    DXT3 = 0x44585433
    DXT4 = 0x44585434
    DXT5 = 0x44585435
    A8R8G8B8 = (3 << 16) | 4
    X8R8G8B8 = (4 << 16) | 4
    A8B8G8R8 = (1 << 16) | 4
    X8B8G8R8 = (2 << 16) | 4
    R8G8B8 = (1 << 16) | 3
    R5G6B5 = (5 << 16) | 2
    
    # RGBA Masks for different formats
    A8R8G8B8_MASKS = [0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000]
    X8R8G8B8_MASKS = [0x00FF0000, 0x0000FF00, 0x000000FF, 0x00000000]
    A8B8G8R8_MASKS = [0x000000FF, 0x0000FF00, 0x00FF0000, 0xFF000000]
    X8B8G8R8_MASKS = [0x000000FF, 0x0000FF00, 0x00FF0000, 0x00000000]
    R8G8B8_MASKS = [0xFF0000, 0x00FF00, 0x0000FF, 0x000000]
    R5G6B5_MASKS = [0xF800, 0x07E0, 0x001F, 0x0000]
    
    # Bit expansion lookup tables for compressed formats
    BIT5 = [0, 8, 16, 25, 33, 41, 49, 58, 66, 74, 82, 90, 99, 107, 115, 123,
            132, 140, 148, 156, 165, 173, 181, 189, 197, 206, 214, 222, 230, 239, 247, 255]
    
    BIT6 = [0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 45, 49, 53, 57, 61, 65, 69, 73, 77,
            81, 85, 89, 93, 97, 101, 105, 109, 113, 117, 121, 125, 130, 134, 138, 142, 146,
            150, 154, 158, 162, 166, 170, 174, 178, 182, 186, 190, 194, 198, 202, 206, 210,
            215, 219, 223, 227, 231, 235, 239, 243, 247, 251, 255]
    BIT5_NP = np.array(BIT5, dtype=np.uint8)
    BIT6_NP = np.array(BIT6, dtype=np.uint8)
    DXT_INDEX_SHIFTS = (np.arange(16, dtype=np.uint32) * 2)
    
    @staticmethod
    def read_dds(filepath: str, mipmap_level: int = 0) -> Optional[wx.Image]:
        """
        Read a DDS file and return a wx.Image.
        
        Args:
            filepath: Path to the DDS file
            mipmap_level: Mipmap level to load (0 = full resolution)
        
        Returns:
            wx.Image or None on error
        """
        try:
            with open(filepath, 'rb') as f:
                # Read DDS header (128 bytes)
                header = f.read(128)
                
                if len(header) < 128:
                    print(f"Error: DDS file too short: {filepath}")
                    return None
                
                # Verify DDS magic number
                magic = header[0:4]
                if magic != b'DDS ':
                    print(f"Error: Not a valid DDS file: {filepath}")
                    return None
                
                # Extract header information
                width = DDSReader._get_width(header)
                height = DDSReader._get_height(header)
                mipmap_count = DDSReader._get_mipmap(header)
                
                print(f"DDS Image: {width}x{height}, Mipmaps: {mipmap_count}")
                
                # Determine format type
                dds_type = DDSReader._get_type(header)
                if dds_type == 0:
                    print(f"Error: Unsupported DDS format in {filepath}")
                    return None
                
                # Calculate offset for mipmap level
                offset = DDSReader._calculate_offset(width, height, dds_type, mipmap_level, mipmap_count)
                
                # Decode based on format
                if dds_type == DDSReader.DXT1:
                    return DDSReader._decode_dxt1(f, width, height, offset)
                elif dds_type == DDSReader.DXT5:
                    return DDSReader._decode_dxt5(f, width, height, offset)
                elif dds_type == DDSReader.A8R8G8B8:
                    return DDSReader._read_a8r8g8b8(f, width, height, offset)
                elif dds_type == DDSReader.X8R8G8B8:
                    return DDSReader._read_x8r8g8b8(f, width, height, offset)
                else:
                    print(f"Error: Format {hex(dds_type)} not implemented")
                    return None
                    
        except Exception as e:
            print(f"Error reading DDS file {filepath}: {e}")
            return None
    
    @staticmethod
    def _get_width(header: bytes) -> int:
        """Extract image width from DDS header"""
        return struct.unpack('<I', header[16:20])[0]
    
    @staticmethod
    def _get_height(header: bytes) -> int:
        """Extract image height from DDS header"""
        return struct.unpack('<I', header[12:16])[0]
    
    @staticmethod
    def _get_mipmap(header: bytes) -> int:
        """Extract mipmap count from DDS header"""
        return struct.unpack('<I', header[28:32])[0]
    
    @staticmethod
    def _get_pixel_format_flags(header: bytes) -> int:
        """Extract pixel format flags"""
        return struct.unpack('<I', header[80:84])[0]
    
    @staticmethod
    def _get_fourcc(header: bytes) -> int:
        """Extract FourCC code (format identifier)"""
        return struct.unpack('>I', header[84:88])[0]  # Big-endian for FourCC
    
    @staticmethod
    def _get_bit_count(header: bytes) -> int:
        """Extract bits per pixel"""
        return struct.unpack('<I', header[88:92])[0]
    
    @staticmethod
    def _get_masks(header: bytes) -> Tuple[int, int, int, int]:
        """Extract RGBA bit masks"""
        red_mask = struct.unpack('<I', header[92:96])[0]
        green_mask = struct.unpack('<I', header[96:100])[0]
        blue_mask = struct.unpack('<I', header[100:104])[0]
        alpha_mask = struct.unpack('<I', header[104:108])[0]
        return red_mask, green_mask, blue_mask, alpha_mask
    
    @staticmethod
    def _get_type(header: bytes) -> int:
        """Determine DDS format type from header"""
        flags = DDSReader._get_pixel_format_flags(header)
        
        # Compressed format (DXT)
        if flags & 0x04:
            return DDSReader._get_fourcc(header)
        
        # Uncompressed RGB format
        elif flags & 0x40:
            bit_count = DDSReader._get_bit_count(header)
            red_mask, green_mask, blue_mask, alpha_mask = DDSReader._get_masks(header)
            
            # Check alpha flag
            if not (flags & 0x01):
                alpha_mask = 0
            
            if bit_count == 32:
                if (red_mask == DDSReader.A8R8G8B8_MASKS[0] and
                    green_mask == DDSReader.A8R8G8B8_MASKS[1] and
                    blue_mask == DDSReader.A8R8G8B8_MASKS[2] and
                    alpha_mask == DDSReader.A8R8G8B8_MASKS[3]):
                    return DDSReader.A8R8G8B8
                
                elif (red_mask == DDSReader.X8R8G8B8_MASKS[0] and
                      green_mask == DDSReader.X8R8G8B8_MASKS[1] and
                      blue_mask == DDSReader.X8R8G8B8_MASKS[2]):
                    return DDSReader.X8R8G8B8
            
            elif bit_count == 24:
                if (red_mask == DDSReader.R8G8B8_MASKS[0] and
                    green_mask == DDSReader.R8G8B8_MASKS[1] and
                    blue_mask == DDSReader.R8G8B8_MASKS[2]):
                    return DDSReader.R8G8B8
        
        return 0
    
    @staticmethod
    def _calculate_offset(width: int, height: int, dds_type: int, 
                         mipmap_level: int, mipmap_count: int) -> int:
        """Calculate file offset to reach specified mipmap level"""
        offset = 0
        
        if mipmap_level > 0 and mipmap_level < mipmap_count:
            for i in range(mipmap_level):
                if dds_type == DDSReader.DXT1:
                    offset += 8 * ((width + 3) // 4) * ((height + 3) // 4)
                elif dds_type in [DDSReader.DXT2, DDSReader.DXT3, DDSReader.DXT4, DDSReader.DXT5]:
                    offset += 16 * ((width + 3) // 4) * ((height + 3) // 4)
                elif dds_type in [DDSReader.A8R8G8B8, DDSReader.X8R8G8B8]:
                    offset += 4 * width * height
                elif dds_type == DDSReader.R8G8B8:
                    offset += 3 * width * height
                
                width //= 2
                height //= 2
            
            width = max(1, width)
            height = max(1, height)
        
        return offset
    
    @staticmethod
    def _decode_dxt1(f, width: int, height: int, offset: int) -> wx.Image:
        """Decode DXT1 (BC1) compressed format"""
        print("Decoding DXT1...")
        t0 = time.perf_counter()

        block_w = (width + 3) // 4
        block_h = (height + 3) // 4
        num_blocks = block_w * block_h
        bytes_needed = num_blocks * 8

        f.seek(128 + offset)
        raw = f.read(bytes_needed)
        if len(raw) < bytes_needed:
            print("Warning: truncated DXT1 data, decoding available blocks only")
            num_blocks = len(raw) // 8
            raw = raw[:num_blocks * 8]
            if num_blocks == 0:
                return None
            block_h = (num_blocks + block_w - 1) // block_w

        blocks = np.frombuffer(raw, dtype=np.uint8).reshape(num_blocks, 8)

        c0 = (blocks[:, 0].astype(np.uint16) | (blocks[:, 1].astype(np.uint16) << 8))
        c1 = (blocks[:, 2].astype(np.uint16) | (blocks[:, 3].astype(np.uint16) << 8))
        bits = (
            blocks[:, 4].astype(np.uint32)
            | (blocks[:, 5].astype(np.uint32) << 8)
            | (blocks[:, 6].astype(np.uint32) << 16)
            | (blocks[:, 7].astype(np.uint32) << 24)
        )

        r0 = DDSReader.BIT5_NP[(c0 >> 11) & 0x1F]
        g0 = DDSReader.BIT6_NP[(c0 >> 5) & 0x3F]
        b0 = DDSReader.BIT5_NP[c0 & 0x1F]
        r1 = DDSReader.BIT5_NP[(c1 >> 11) & 0x1F]
        g1 = DDSReader.BIT6_NP[(c1 >> 5) & 0x3F]
        b1 = DDSReader.BIT5_NP[c1 & 0x1F]

        colors = np.zeros((num_blocks, 4, 3), dtype=np.uint8)
        colors[:, 0, 0], colors[:, 0, 1], colors[:, 0, 2] = r0, g0, b0
        colors[:, 1, 0], colors[:, 1, 1], colors[:, 1, 2] = r1, g1, b1

        c0_gt_c1 = c0 > c1
        not_c0_gt_c1 = ~c0_gt_c1

        r2 = ((2 * r0.astype(np.uint16) + r1.astype(np.uint16)) // 3).astype(np.uint8)
        g2 = ((2 * g0.astype(np.uint16) + g1.astype(np.uint16)) // 3).astype(np.uint8)
        b2 = ((2 * b0.astype(np.uint16) + b1.astype(np.uint16)) // 3).astype(np.uint8)
        r2_alt = ((r0.astype(np.uint16) + r1.astype(np.uint16)) // 2).astype(np.uint8)
        g2_alt = ((g0.astype(np.uint16) + g1.astype(np.uint16)) // 2).astype(np.uint8)
        b2_alt = ((b0.astype(np.uint16) + b1.astype(np.uint16)) // 2).astype(np.uint8)

        colors[c0_gt_c1, 2, 0] = r2[c0_gt_c1]
        colors[c0_gt_c1, 2, 1] = g2[c0_gt_c1]
        colors[c0_gt_c1, 2, 2] = b2[c0_gt_c1]
        colors[not_c0_gt_c1, 2, 0] = r2_alt[not_c0_gt_c1]
        colors[not_c0_gt_c1, 2, 1] = g2_alt[not_c0_gt_c1]
        colors[not_c0_gt_c1, 2, 2] = b2_alt[not_c0_gt_c1]

        r3 = ((r0.astype(np.uint16) + 2 * r1.astype(np.uint16)) // 3).astype(np.uint8)
        g3 = ((g0.astype(np.uint16) + 2 * g1.astype(np.uint16)) // 3).astype(np.uint8)
        b3 = ((b0.astype(np.uint16) + 2 * b1.astype(np.uint16)) // 3).astype(np.uint8)
        colors[c0_gt_c1, 3, 0] = r3[c0_gt_c1]
        colors[c0_gt_c1, 3, 1] = g3[c0_gt_c1]
        colors[c0_gt_c1, 3, 2] = b3[c0_gt_c1]
        # when c0 <= c1, color index 3 is transparent/black in DXT1 without alpha
        colors[not_c0_gt_c1, 3, :] = 0

        indices = ((bits[:, None] >> DDSReader.DXT_INDEX_SHIFTS[None, :]) & 0x03).astype(np.uint8)
        block_pixels = colors[np.arange(num_blocks)[:, None], indices]  # (num_blocks, 16, 3)

        # Recompose full image from 4x4 blocks
        blocks_reshaped = block_pixels.reshape(block_h, block_w, 4, 4, 3)
        pixels = blocks_reshaped.transpose(0, 2, 1, 3, 4).reshape(block_h * 4, block_w * 4, 3)
        pixels = pixels[:height, :width, :]

        img = wx.Image(width, height)
        img.SetData(pixels.tobytes())
        elapsed = time.perf_counter() - t0
        print(f"Done in {elapsed:.3f} seconds")
        return img
    
    @staticmethod
    def _get_dxt_color(c0: int, c1: int, index: int) -> Tuple[int, int, int]:
        """Calculate DXT color from reference colors and index"""
        # Extract RGB565 components for c0
        r0 = DDSReader.BIT5[(c0 & 0xFC00) >> 11]
        g0 = DDSReader.BIT6[(c0 & 0x07E0) >> 5]
        b0 = DDSReader.BIT5[c0 & 0x001F]
        
        # Extract RGB565 components for c1
        r1 = DDSReader.BIT5[(c1 & 0xFC00) >> 11]
        g1 = DDSReader.BIT6[(c1 & 0x07E0) >> 5]
        b1 = DDSReader.BIT5[c1 & 0x001F]
        
        if index == 0:
            return (r0, g0, b0)
        elif index == 1:
            return (r1, g1, b1)
        elif index == 2:
            if c0 > c1:
                # 2/3 c0 + 1/3 c1
                r = (2 * r0 + r1) // 3
                g = (2 * g0 + g1) // 3
                b = (2 * b0 + b1) // 3
            else:
                # (c0 + c1) / 2
                r = (r0 + r1) // 2
                g = (g0 + g1) // 2
                b = (b0 + b1) // 2
            return (r, g, b)
        else:  # index == 3
            if c0 > c1:
                # 1/3 c0 + 2/3 c1
                r = (r0 + 2 * r1) // 3
                g = (g0 + 2 * g1) // 3
                b = (b0 + 2 * b1) // 3
                return (r, g, b)
            else:
                # Transparent (black)
                return (0, 0, 0)
    
    @staticmethod
    def _decode_dxt5(f, width: int, height: int, offset: int) -> wx.Image:
        """Decode DXT5 (BC3) compressed format with alpha"""
        print("Decoding DXT5...")
        t0 = time.perf_counter()
        
        # Create numpy array for RGBA pixel data
        pixels = np.zeros((height, width, 4), dtype=np.uint8)
        
        # Seek to data start
        f.seek(128 + offset)
        
        # Process 4x4 blocks
        for y in range(0, height, 4):
            for x in range(0, width, 4):
                # Read one DXT5 block (16 bytes)
                block = f.read(16)
                if len(block) < 16:
                    break
                
                # Alpha data (8 bytes)
                a0 = block[0]
                a1 = block[1]
                alpha_bits = struct.unpack('<Q', block[2:8] + b'\x00\x00')[0]
                
                # Color data (8 bytes)
                c0 = struct.unpack('<H', block[8:10])[0]
                c1 = struct.unpack('<H', block[10:12])[0]
                bits = struct.unpack('<I', block[12:16])[0]
                
                # Decode 4x4 block
                for j in range(4):
                    for i in range(4):
                        # Color index
                        color_index = (bits >> (2 * (4 * j + i))) & 0x03
                        r, g, b = DDSReader._get_dxt_color(c0, c1, color_index)
                        
                        # Alpha index
                        alpha_index = (alpha_bits >> (3 * (4 * j + i))) & 0x07
                        a = DDSReader._get_dxt5_alpha(a0, a1, alpha_index)
                        
                        # Set pixel
                        px = x + i
                        py = y + j
                        if px < width and py < height:
                            pixels[py, px] = [r, g, b, a]
        
        # Convert to wx.Image with alpha
        img = wx.Image(width, height)
        rgb_data = pixels[:, :, :3].tobytes()
        alpha_data = pixels[:, :, 3].tobytes()
        img.SetData(rgb_data)
        img.SetAlpha(alpha_data)
        elapsed = time.perf_counter() - t0
        print(f"Done in {elapsed:.3f} seconds")
        return img
    
    @staticmethod
    def _get_dxt5_alpha(a0: int, a1: int, index: int) -> int:
        """Calculate DXT5 alpha value from reference alphas and index"""
        if a0 > a1:
            if index == 0:
                return a0
            elif index == 1:
                return a1
            elif index == 2:
                return (6 * a0 + a1) // 7
            elif index == 3:
                return (5 * a0 + 2 * a1) // 7
            elif index == 4:
                return (4 * a0 + 3 * a1) // 7
            elif index == 5:
                return (3 * a0 + 4 * a1) // 7
            elif index == 6:
                return (2 * a0 + 5 * a1) // 7
            else:  # index == 7
                return (a0 + 6 * a1) // 7
        else:
            if index == 0:
                return a0
            elif index == 1:
                return a1
            elif index == 2:
                return (4 * a0 + a1) // 5
            elif index == 3:
                return (3 * a0 + 2 * a1) // 5
            elif index == 4:
                return (2 * a0 + 3 * a1) // 5
            elif index == 5:
                return (a0 + 4 * a1) // 5
            elif index == 6:
                return 0
            else:  # index == 7
                return 255
    
    @staticmethod
    def _read_a8r8g8b8(f, width: int, height: int, offset: int) -> wx.Image:
        """Read uncompressed A8R8G8B8 format"""
        print("Reading A8R8G8B8...")
        t0 = time.perf_counter()

        f.seek(128 + offset)
        raw = f.read(width * height * 4)
        if len(raw) < width * height * 4:
            print("Error: truncated A8R8G8B8 data")
            return None

        src = np.frombuffer(raw, dtype=np.uint8).reshape(height, width, 4)
        # Source is BGRA in DDS stream for this format.
        pixels = src[:, :, [2, 1, 0, 3]]
        
        # Convert to wx.Image with alpha
        img = wx.Image(width, height)
        rgb_data = pixels[:, :, :3].tobytes()
        alpha_data = pixels[:, :, 3].tobytes()
        img.SetData(rgb_data)
        img.SetAlpha(alpha_data)
        elapsed = time.perf_counter() - t0
        print(f"Done in {elapsed:.3f} seconds")
        return img
    
    @staticmethod
    def _read_x8r8g8b8(f, width: int, height: int, offset: int) -> wx.Image:
        """Read uncompressed X8R8G8B8 format (no alpha)"""
        print("Reading X8R8G8B8...")
        t0 = time.perf_counter()

        f.seek(128 + offset)
        raw = f.read(width * height * 4)
        if len(raw) < width * height * 4:
            print("Error: truncated X8R8G8B8 data")
            return None

        src = np.frombuffer(raw, dtype=np.uint8).reshape(height, width, 4)
        # Source is BGRX; keep RGB only.
        pixels = src[:, :, [2, 1, 0]]
        
        # Convert to wx.Image
        img = wx.Image(width, height)
        img.SetData(pixels.tobytes())
        elapsed = time.perf_counter() - t0
        print(f"Done in {elapsed:.3f} seconds")
        return img


def convert_dds_to_png(dds_path: str, png_path: str) -> bool:
    """
    Convert a DDS file to PNG format.
    
    Args:
        dds_path: Path to input DDS file
        png_path: Path to output PNG file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        img = DDSReader.read_dds(dds_path)
        if img:
            img.SaveFile(png_path, wx.BITMAP_TYPE_PNG)
            print(f"✓ Saved: {png_path}")
            return True
        else:
            print(f"✗ Failed to decode: {dds_path}")
            return False
    except Exception as e:
        print(f"✗ Error converting {dds_path}: {e}")
        return False


# Command-line usage
if __name__ == '__main__':
    import sys
    
    app = wx.App(False)  # wxPython requires an app instance
    
    if len(sys.argv) < 2:
        print("Usage: python dds_reader.py <dds_file> [output.png]")
        print("  If output path is not specified, uses input filename with .png extension")
        sys.exit(1)
    
    dds_file = sys.argv[1]
    png_file = sys.argv[2] if len(sys.argv) > 2 else dds_file.replace('.dds', '.png')
    
    print(f"Converting {dds_file} → {png_file}...")
    if convert_dds_to_png(dds_file, png_file):
        print("✓ Conversion successful!")
    else:
        print("✗ Conversion failed")
        sys.exit(1)
