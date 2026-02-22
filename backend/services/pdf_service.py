"""PDF处理服务模块，集成pdfly的核心功能"""

from pathlib import Path
from io import BytesIO
import shutil
from typing import List, Dict, Any
import logging

from pypdf import PdfReader, PdfWriter

logger = logging.getLogger(__name__)


class PdfService:
    """PDF处理服务类，提供各种PDF操作功能"""
    
    def __init__(self):
        """初始化PDF服务"""
        pass
    
    def extract_images(self, pdf_path: str) -> List[Dict[str, Any]]:
        """从PDF文件中提取图片
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            提取的图片信息列表，包含路径、名称等
        """
        try:
            pdf = Path(pdf_path)
            reader = PdfReader(str(pdf))
            extracted_images = []
            
            # 获取下载目录
            from main import DOWNLOAD_DIR
            
            # 创建保存图片的目录
            pdf_stem = pdf.stem
            # 检查是否是UUID格式的文件ID
            import re
            if re.match(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$', pdf_stem):
                # 如果是UUID格式，直接使用作为目录名
                output_dir = DOWNLOAD_DIR / pdf_stem
            else:
                # 否则，从路径中提取文件ID
                # 假设文件路径格式为：UPLOAD_DIR / {file_id}.pdf
                file_id = pdf_stem
                output_dir = DOWNLOAD_DIR / file_id
            output_dir.mkdir(exist_ok=True)
            
            for page_index, page in enumerate(reader.pages):
                for image_file_object in page.images:
                    image_path = output_dir / f"{page_index:04d}-{image_file_object.name}"
                    with open(image_path, "wb") as fp:
                        fp.write(image_file_object.data)
                    # 返回相对于下载目录的路径，而不是完整路径
                    relative_path = image_path.relative_to(DOWNLOAD_DIR)
                    extracted_images.append({
                        "path": str(relative_path),
                        "name": image_file_object.name,
                        "page": page_index + 1,
                        "size": len(image_file_object.data)
                    })
            
            logger.info(f"从PDF中提取了 {len(extracted_images)} 张图片")
            return extracted_images
        except Exception as e:
            logger.error(f"提取PDF图片失败: {str(e)}")
            raise
    
    def compress_pdf(self, pdf_path: str, output_path: str) -> Dict[str, Any]:
        """压缩PDF文件
        
        Args:
            pdf_path: 输入PDF文件路径
            output_path: 输出PDF文件路径
            
        Returns:
            压缩结果信息，包含原始大小、压缩后大小等
        """
        try:
            pdf = Path(pdf_path)
            output = Path(output_path)
            
            reader = PdfReader(pdf)
            writer = PdfWriter()
            
            # 添加所有页面
            for page in reader.pages:
                writer.add_page(page)
            
            # 保留元数据
            if reader.metadata:
                writer.add_metadata(reader.metadata)
            
            # 压缩内容流
            for page in writer.pages:
                page.compress_content_streams()
            
            # 先写入内存缓冲区
            compressed_buffer = BytesIO()
            writer.write(compressed_buffer)
            compressed_data = compressed_buffer.getvalue()
            comp_size = len(compressed_data)
            
            # 获取原始文件大小
            orig_size = pdf.stat().st_size
            
            # 如果压缩后更大，使用原始文件
            if comp_size >= orig_size:
                logger.warning(f"压缩结果更大 ({comp_size} >= {orig_size} bytes)，使用原始文件")
                shutil.copy2(pdf, output)
                final_size = orig_size
                ratio = 100.0
                status = "No compression applied (would increase size)"
            else:
                with open(output, "wb") as fp:
                    fp.write(compressed_data)
                final_size = comp_size
                ratio = (comp_size / orig_size) * 100
                status = f"Compressed ({ratio:.1f}% of original)"
            
            result = {
                "original_size": orig_size,
                "compressed_size": final_size,
                "compression_ratio": ratio,
                "status": status,
                "output_path": str(output)
            }
            
            logger.info(f"PDF压缩完成: {result}")
            return result
        except Exception as e:
            logger.error(f"压缩PDF失败: {str(e)}")
            raise
    
    def extract_text(self, pdf_path: str) -> str:
        """从PDF文件中提取文本
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            提取的文本内容
        """
        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += (page.extract_text() or "") + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"提取PDF文本失败: {str(e)}")
            raise
    
    def rotate_pdf(self, pdf_path: str, output_path: str, degrees: int, pages: str = ":") -> Dict[str, Any]:
        """旋转PDF页面
        
        Args:
            pdf_path: 输入PDF文件路径
            output_path: 输出PDF文件路径
            degrees: 旋转角度
            pages: 页面范围（如 ":" 表示所有页面，"1-5" 表示1-5页）
            
        Returns:
            旋转结果信息
        """
        try:
            pdf = Path(pdf_path)
            output = Path(output_path)
            
            reader = PdfReader(pdf)
            writer = PdfWriter()
            
            # 解析页面范围
            if pages == ":":
                page_indices = range(len(reader.pages))
            else:
                page_indices = []
                for part in pages.split(","):
                    if "-" in part:
                        start, end = map(int, part.split("-"))
                        page_indices.extend(range(start-1, end))
                    else:
                        page_indices.append(int(part)-1)
            
            # 旋转指定页面
            for i, page in enumerate(reader.pages):
                if i in page_indices:
                    page.rotate(degrees)
                writer.add_page(page)
            
            # 保留元数据
            if reader.metadata:
                writer.add_metadata(reader.metadata)
            
            with open(output, "wb") as fp:
                writer.write(fp)
            
            result = {
                "output_path": str(output),
                "rotated_pages": [i+1 for i in page_indices],
                "degrees": degrees
            }
            
            logger.info(f"PDF页面旋转完成: {result}")
            return result
        except Exception as e:
            logger.error(f"旋转PDF页面失败: {str(e)}")
            raise
    
    def merge_pdfs(self, pdf_paths: List[str], output_path: str) -> Dict[str, Any]:
        """合并多个PDF文件
        
        Args:
            pdf_paths: 要合并的PDF文件路径列表
            output_path: 输出PDF文件路径
            
        Returns:
            合并结果信息
        """
        try:
            writer = PdfWriter()
            
            for pdf_path in pdf_paths:
                reader = PdfReader(pdf_path)
                for page in reader.pages:
                    writer.add_page(page)
            
            with open(output_path, "wb") as fp:
                writer.write(fp)
            
            result = {
                "output_path": output_path,
                "merged_files": pdf_paths,
                "total_pages": len(writer.pages)
            }
            
            logger.info(f"PDF合并完成: {result}")
            return result
        except Exception as e:
            logger.error(f"合并PDF失败: {str(e)}")
            raise
    
    def split_pdf(self, pdf_path: str, output_dir: str, split_page: int = None, pages_per_file: int = None) -> List[Dict[str, Any]]:
        """将PDF文件拆分
        
        Args:
            pdf_path: 输入PDF文件路径
            output_dir: 输出目录
            split_page: 拆分位置，如果提供则按此位置拆分为两个文件
            pages_per_file: 每页包含的页数，如果提供则按此页数进行分页
            
        Returns:
            拆分结果信息列表
        """
        try:
            pdf = Path(pdf_path)
            output = Path(output_dir)
            output.mkdir(exist_ok=True)
            
            reader = PdfReader(pdf)
            results = []
            total_pages = len(reader.pages)
            
            if split_page is not None:
                # 按指定位置拆分
                if split_page < 1 or split_page >= total_pages:
                    raise ValueError(f"拆分位置必须在1到{total_pages-1}之间")
                
                # 第一个文件：1到split_page页
                writer1 = PdfWriter()
                for i in range(split_page):
                    writer1.add_page(reader.pages[i])
                output_path1 = output / f"{pdf.stem}_part1_1-{split_page}.pdf"
                with open(output_path1, "wb") as fp:
                    writer1.write(fp)
                results.append({
                    "pages": f"1-{split_page}",
                    "path": str(output_path1),
                    "file_name": output_path1.name
                })
                
                # 第二个文件：split_page+1到最后一页
                writer2 = PdfWriter()
                for i in range(split_page, total_pages):
                    writer2.add_page(reader.pages[i])
                output_path2 = output / f"{pdf.stem}_part2_{split_page+1}-{total_pages}.pdf"
                with open(output_path2, "wb") as fp:
                    writer2.write(fp)
                results.append({
                    "pages": f"{split_page+1}-{total_pages}",
                    "path": str(output_path2),
                    "file_name": output_path2.name
                })
            elif pages_per_file is not None:
                # 按指定页数进行分页
                if pages_per_file < 1:
                    raise ValueError(f"每页包含的页数必须大于0")
                
                part_number = 1
                for start_page in range(0, total_pages, pages_per_file):
                    end_page = min(start_page + pages_per_file, total_pages)
                    
                    writer = PdfWriter()
                    for i in range(start_page, end_page):
                        writer.add_page(reader.pages[i])
                    
                    # 保留元数据
                    if reader.metadata:
                        writer.add_metadata(reader.metadata)
                    
                    output_path = output / f"{pdf.stem}_part{part_number}_{start_page+1}-{end_page}.pdf"
                    with open(output_path, "wb") as fp:
                        writer.write(fp)
                    
                    results.append({
                        "pages": f"{start_page+1}-{end_page}",
                        "path": str(output_path),
                        "file_name": output_path.name
                    })
                    part_number += 1
            else:
                # 按页拆分
                for i, page in enumerate(reader.pages):
                    writer = PdfWriter()
                    writer.add_page(page)
                    
                    output_path = output / f"{pdf.stem}_page_{i+1}.pdf"
                    with open(output_path, "wb") as fp:
                        writer.write(fp)
                    
                    results.append({
                        "page": i+1,
                        "path": str(output_path),
                        "file_name": output_path.name
                    })
            
            logger.info(f"PDF拆分完成，共生成 {len(results)} 个文件")
            return results
        except Exception as e:
            logger.error(f"拆分PDF失败: {str(e)}")
            raise
    
    def get_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """获取PDF文件的元数据
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            PDF元数据字典
        """
        try:
            reader = PdfReader(pdf_path)
            metadata = {}
            
            if reader.metadata:
                for key, value in reader.metadata.items():
                    # 转换PyPDF的元数据键格式
                    if key.startswith("/Creator"):
                        metadata["creator"] = value
                    elif key.startswith("/Producer"):
                        metadata["producer"] = value
                    elif key.startswith("/Title"):
                        metadata["title"] = value
                    elif key.startswith("/Subject"):
                        metadata["subject"] = value
                    elif key.startswith("/Author"):
                        metadata["author"] = value
                    elif key.startswith("/Keywords"):
                        metadata["keywords"] = value
                    elif key.startswith("/CreationDate"):
                        metadata["creation_date"] = value
                    elif key.startswith("/ModDate"):
                        metadata["modification_date"] = value
            
            metadata["total_pages"] = len(reader.pages)
            
            logger.info(f"获取PDF元数据: {metadata}")
            return metadata
        except Exception as e:
            logger.error(f"获取PDF元数据失败: {str(e)}")
            raise


# 创建PDF服务单例
pdf_service = PdfService()