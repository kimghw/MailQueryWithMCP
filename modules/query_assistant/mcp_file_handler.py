"""
MCP Server File Handler - PDF 및 바이너리 파일 처리
"""
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional
from mcp.types import TextContent, ImageContent, Tool
import mimetypes

class MCPFileHandler:
    """MCP 서버에서 파일을 처리하는 핸들러"""
    
    def __init__(self):
        self.supported_text_formats = {'.txt', '.md', '.json', '.xml', '.csv'}
        self.supported_image_formats = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
        
    def create_file_tools(self) -> List[Tool]:
        """파일 관련 MCP 도구 생성"""
        return [
            Tool(
                name="read_file_as_text",
                description="파일을 텍스트로 읽어서 반환",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "읽을 파일의 경로"
                        }
                    },
                    "required": ["file_path"]
                }
            ),
            Tool(
                name="read_file_as_base64",
                description="파일을 Base64로 인코딩하여 반환 (PDF, 이미지 등)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "읽을 파일의 경로"
                        },
                        "include_mime_type": {
                            "type": "boolean",
                            "description": "MIME 타입 포함 여부",
                            "default": True
                        }
                    },
                    "required": ["file_path"]
                }
            ),
            Tool(
                name="read_pdf_with_conversion",
                description="PDF를 텍스트로 변환하여 반환",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "PDF 파일 경로"
                        },
                        "max_pages": {
                            "type": "integer",
                            "description": "최대 변환 페이지 수",
                            "default": 50
                        }
                    },
                    "required": ["file_path"]
                }
            )
        ]
    
    async def handle_read_file_as_text(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """텍스트 파일 읽기"""
        file_path = Path(arguments['file_path'])
        
        if not file_path.exists():
            return [TextContent(
                type="text",
                text=f"Error: File not found - {file_path}"
            )]
        
        if file_path.suffix.lower() not in self.supported_text_formats:
            return [TextContent(
                type="text",
                text=f"Error: Unsupported text format - {file_path.suffix}"
            )]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return [TextContent(
                type="text",
                text=content
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error reading file: {str(e)}"
            )]
    
    async def handle_read_file_as_base64(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """파일을 Base64로 인코딩하여 반환"""
        file_path = Path(arguments['file_path'])
        include_mime = arguments.get('include_mime_type', True)
        
        if not file_path.exists():
            return [TextContent(
                type="text",
                text=f"Error: File not found - {file_path}"
            )]
        
        try:
            # 파일 읽기
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Base64 인코딩
            base64_content = base64.b64encode(file_content).decode('utf-8')
            
            # MIME 타입 추가
            if include_mime:
                mime_type, _ = mimetypes.guess_type(str(file_path))
                if not mime_type:
                    mime_type = 'application/octet-stream'
                
                # Data URI 형식으로 반환
                data_uri = f"data:{mime_type};base64,{base64_content}"
                
                return [TextContent(
                    type="text",
                    text=data_uri
                )]
            else:
                return [TextContent(
                    type="text",
                    text=base64_content
                )]
                
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error encoding file: {str(e)}"
            )]
    
    async def handle_read_pdf_with_conversion(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """PDF를 텍스트로 변환"""
        file_path = Path(arguments['file_path'])
        max_pages = arguments.get('max_pages', 50)
        
        if not file_path.exists():
            return [TextContent(
                type="text",
                text=f"Error: File not found - {file_path}"
            )]
        
        if file_path.suffix.lower() != '.pdf':
            return [TextContent(
                type="text",
                text=f"Error: Not a PDF file - {file_path}"
            )]
        
        try:
            # FileConverter 사용
            from modules.mail_attachment import FileConverter
            converter = FileConverter()
            
            if not converter.dependencies['pdf']:
                return [TextContent(
                    type="text",
                    text="Error: PyPDF2 not installed. Cannot convert PDF."
                )]
            
            # PDF 변환
            text_content = converter.convert_to_text(file_path)
            
            # 페이지 수 제한
            lines = text_content.split('\n')
            page_markers = [i for i, line in enumerate(lines) if line.startswith('--- Page')]
            
            if len(page_markers) > max_pages:
                # max_pages까지만 포함
                cutoff_index = page_markers[max_pages]
                text_content = '\n'.join(lines[:cutoff_index])
                text_content += f"\n\n[Note: Truncated to first {max_pages} pages]"
            
            return [TextContent(
                type="text",
                text=text_content
            )]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error converting PDF: {str(e)}"
            )]


# MCP 서버에 통합하는 예제
async def integrate_file_handler_to_mcp(mcp_server):
    """MCP 서버에 파일 핸들러 통합"""
    file_handler = MCPFileHandler()
    
    # 도구 등록
    tools = file_handler.create_file_tools()
    # mcp_server에 tools 추가하는 로직
    
    # 핸들러 등록
    @mcp_server.call_tool()
    async def handle_file_tool(name: str, arguments: Dict[str, Any]):
        if name == "read_file_as_text":
            return await file_handler.handle_read_file_as_text(arguments)
        elif name == "read_file_as_base64":
            return await file_handler.handle_read_file_as_base64(arguments)
        elif name == "read_pdf_with_conversion":
            return await file_handler.handle_read_pdf_with_conversion(arguments)
        else:
            raise ValueError(f"Unknown file tool: {name}")