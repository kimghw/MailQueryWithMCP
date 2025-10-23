"""SharePoint uploader using Playwright browser automation"""

import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class SharePointUploader:
    """SharePoint 파일 업로드 (Playwright 브라우저 자동화)"""

    def __init__(self, folder_url: str, headless: bool = True):
        """
        Initialize SharePoint uploader

        Args:
            folder_url: SharePoint folder shared URL
            headless: Run browser in headless mode (default: True)
        """
        self.folder_url = folder_url
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        logger.info(f"SharePointUploader initialized with folder_url={folder_url}, headless={headless}")

    async def _ensure_browser(self):
        """브라우저 인스턴스 확인 및 초기화"""
        if self.browser is None:
            try:
                from playwright.async_api import async_playwright
                self.playwright = await async_playwright().start()
                self.browser = await self.playwright.chromium.launch(headless=self.headless)
                self.context = await self.browser.new_context()
                self.page = await self.context.new_page()
                logger.info("Playwright browser launched")
            except ImportError:
                logger.error("Playwright not installed. Install with: pip install playwright && playwright install chromium")
                raise
            except Exception as e:
                logger.error(f"Failed to launch browser: {str(e)}")
                raise

    async def _navigate_to_folder(self) -> bool:
        """SharePoint 폴더로 이동"""
        try:
            logger.info(f"Navigating to SharePoint folder: {self.folder_url}")
            await self.page.goto(self.folder_url, wait_until='domcontentloaded', timeout=30000)

            # 로그인 필요 여부 확인
            current_url = self.page.url
            if 'login.microsoftonline.com' in current_url:
                logger.warning("Login required. User must authenticate manually.")
                # headless=False 모드에서는 사용자가 수동 로그인 가능
                if not self.headless:
                    logger.info("Waiting 60 seconds for manual login...")
                    await self.page.wait_for_timeout(60000)
                else:
                    logger.error("Cannot login in headless mode. Set headless=False for manual login.")
                    return False

            logger.info("Successfully navigated to SharePoint folder")
            return True

        except Exception as e:
            logger.error(f"Failed to navigate to SharePoint folder: {str(e)}")
            return False

    async def _find_upload_button(self) -> Optional[Any]:
        """업로드 버튼 찾기"""
        possible_selectors = [
            'button[name="Upload"]',
            'button:has-text("Upload")',
            'button:has-text("업로드")',
            '[data-automationid="uploadButton"]',
            'button[aria-label*="Upload"]',
            'button[aria-label*="업로드"]'
        ]

        for selector in possible_selectors:
            try:
                upload_button = await self.page.wait_for_selector(selector, timeout=5000)
                if upload_button:
                    logger.info(f"Found upload button with selector: {selector}")
                    return upload_button
            except Exception:
                continue

        logger.warning("Upload button not found")
        return None

    async def _find_files_menu_item(self) -> Optional[Any]:
        """Files 메뉴 항목 찾기"""
        possible_file_menus = [
            'button:has-text("Files")',
            'button:has-text("파일")',
            '[role="menuitem"]:has-text("Files")',
            '[role="menuitem"]:has-text("파일")',
            'li:has-text("Files")',
            'li:has-text("파일")'
        ]

        for selector in possible_file_menus:
            try:
                files_menu_item = await self.page.wait_for_selector(selector, timeout=3000)
                if files_menu_item:
                    logger.info(f"Found Files menu item with selector: {selector}")
                    return files_menu_item
            except Exception:
                continue

        logger.warning("Files menu item not found")
        return None

    async def upload_file(
        self,
        file_path: Path,
        folder_name: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload a single file to SharePoint

        Args:
            file_path: Path to file to upload
            folder_name: Optional subfolder name (not used - uploads to root)
            user_id: Optional user ID (not used)

        Returns:
            Dictionary with upload result
        """
        try:
            await self._ensure_browser()

            # Navigate to SharePoint folder
            if not await self._navigate_to_folder():
                return {"success": False, "error": "Failed to navigate to SharePoint folder"}

            # Find and click Upload button
            upload_button = await self._find_upload_button()
            if not upload_button:
                return {"success": False, "error": "Upload button not found"}

            await upload_button.click()
            await self.page.wait_for_timeout(500)

            # Find and click Files menu item
            files_menu_item = await self._find_files_menu_item()
            if not files_menu_item:
                return {"success": False, "error": "Files menu item not found"}

            # Set up file chooser handler and click
            async with self.page.expect_file_chooser(timeout=10000) as fc_info:
                await files_menu_item.click()

            file_chooser = await fc_info.value
            await file_chooser.set_files(str(file_path))

            # Wait for upload to complete
            await self.page.wait_for_timeout(3000)

            logger.info(f"Successfully uploaded file: {file_path.name}")
            return {
                "success": True,
                "message": f"Uploaded {file_path.name} to SharePoint",
                "file_name": file_path.name
            }

        except Exception as e:
            logger.error(f"Failed to upload file {file_path}: {str(e)}")
            return {"success": False, "error": str(e)}

    async def upload_files(
        self,
        file_paths: List[Path],
        folder_name: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload multiple files to SharePoint at once

        Args:
            file_paths: List of file paths to upload
            folder_name: Optional subfolder name (not used)
            user_id: Optional user ID (not used)

        Returns:
            Dictionary with upload results
        """
        try:
            await self._ensure_browser()

            # Navigate to SharePoint folder
            if not await self._navigate_to_folder():
                return {"success": False, "error": "Failed to navigate to SharePoint folder"}

            # Find and click Upload button
            upload_button = await self._find_upload_button()
            if not upload_button:
                return {"success": False, "error": "Upload button not found"}

            await upload_button.click()
            await self.page.wait_for_timeout(500)

            # Find and click Files menu item
            files_menu_item = await self._find_files_menu_item()
            if not files_menu_item:
                return {"success": False, "error": "Files menu item not found"}

            # Set up file chooser handler and click
            async with self.page.expect_file_chooser(timeout=10000) as fc_info:
                await files_menu_item.click()

            file_chooser = await fc_info.value
            # Upload all files at once
            await file_chooser.set_files([str(fp) for fp in file_paths])

            # Wait for upload to complete
            await self.page.wait_for_timeout(5000)

            logger.info(f"Successfully uploaded {len(file_paths)} files to SharePoint")
            return {
                "success": True,
                "message": f"Uploaded {len(file_paths)} files to SharePoint",
                "file_count": len(file_paths),
                "file_names": [fp.name for fp in file_paths]
            }

        except Exception as e:
            logger.error(f"Failed to upload files: {str(e)}")
            return {"success": False, "error": str(e)}

    async def close(self):
        """브라우저 종료"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")

    async def __aenter__(self):
        """Context manager enter"""
        await self._ensure_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close()
