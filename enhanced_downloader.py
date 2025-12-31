#!/usr/bin/env python3
"""
Enhanced bulk downloader with support for multiple document types and progress callbacks.
Uses ThreadPoolExecutor for concurrent downloads with configurable worker count.
"""

import os
import re
import json
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

class EnhancedDownloader:
    def __init__(self, base_url="http://real-base-url-is.hidden", max_workers=5): # Contact the developer for the real base url
        self.base_url = base_url
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.5",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{base_url}/pengajuan"
        })
        
        # Progress tracking
        self.is_downloading = False
        self.should_stop = False
        self.current_package = 0
        self.total_packages = 0
        self.downloaded_files = 0
        self.skipped_files = 0
        self.error_count = 0
        self.processed_count = 0
        
        # Thread-safe lock for counters
        self._lock = threading.Lock()
        
        # Progress callback
        self.progress_callback = None
        self.status_callback = None
    
    def set_session_cookie(self, session_cookie):
        """Set the session cookie for the downloader."""
        if "ci_session=" not in session_cookie:
            session_cookie = f"ci_session={session_cookie}"
        self.session.headers["Cookie"] = session_cookie
    
    def set_callbacks(self, progress_callback=None, status_callback=None):
        """Set progress and status callbacks."""
        self.progress_callback = progress_callback
        self.status_callback = status_callback
    
    def update_progress(self, current, total, message=""):
        """Update progress and call callback if set."""
        self.current_package = current
        self.total_packages = total
        if self.progress_callback:
            try:
                percentage = (current / total) * 100 if total > 0 else 0
                self.progress_callback(current, total, percentage, message)
            except Exception as e:
                print(f"Progress callback error: {e}")
    
    def update_status(self, message, level="info"):
        """Update status message and call callback if set."""
        if self.status_callback:
            try:
                self.status_callback(message, level)
            except Exception as e:
                print(f"Status callback error: {e}")
    
    def stop_download(self):
        """Stop the download process."""
        self.should_stop = True
    
    def _increment_downloaded(self):
        """Thread-safe increment for downloaded files counter."""
        with self._lock:
            self.downloaded_files += 1
    
    def _increment_skipped(self):
        """Thread-safe increment for skipped files counter."""
        with self._lock:
            self.skipped_files += 1
    
    def _increment_error(self):
        """Thread-safe increment for error counter."""
        with self._lock:
            self.error_count += 1
    
    def _increment_processed(self):
        """Thread-safe increment for processed counter and update progress."""
        with self._lock:
            self.processed_count += 1
            return self.processed_count
    
    def get_packages(self):
        """Fetch all packages from the system."""
        try:
            self.update_status("Fetching packages from server...")
            response = self.session.get(f"{self.base_url}/pengajuan/data_pengajuan_ajax")
            response.raise_for_status()
            
            packages_data = response.json()
            all_packages = packages_data.get("data", [])
            
            self.update_status(f"Found {len(all_packages)} packages")
            return all_packages
            
        except Exception as e:
            self.update_status(f"Error fetching packages: {e}", "error")
            return []
    
    def parse_package(self, row):
        """Parse a package row to extract information."""
        try:
            # Row format: [index, link_html, nik, nama, phone, status_html, date_html]
            link_html = row[1]
            nik = row[2]
            nama = row[3]
            
            # Extract package code and number from the link HTML
            link_match = re.search(r'href="pengajuan/lihat_paket/([^"]+)"[^>]*>([^<]+)</a>', link_html)
            
            if link_match:
                kode_paket_encoded = link_match.group(1)
                nomor_paket = link_match.group(2)
                
                return {
                    "kode_paket": kode_paket_encoded,
                    "nomor": nomor_paket,
                    "nama": nama,
                    "nik": nik
                }
        except Exception as e:
            self.update_status(f"Error parsing package: {e}", "error")
        
        return None
    
    def check_package_documents(self, package, document_types):
        """Check a package for specified document types and download if found."""
        if self.should_stop:
            return False
        
        try:
            # Fetch document details for this package
            response = self.session.post(
                f"{self.base_url}/pengajuan/dokumencetak",
                data={
                    "kode_paket": package['kode_paket'],
                    "nomor": package['nomor'],
                    "nama": package['nama']
                }
            )
            
            if response.status_code != 200:
                self._increment_error()
                return False
            
            # Parse response
            try:
                json_response = response.json()
                if json_response.get("status") != "success":
                    self._increment_error()
                    return False
                html = json_response.get("data", "")
            except:
                # Fallback to treating as HTML if JSON parsing fails
                html = response.text

            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all document sections (each has a table with document info)
            tables = soup.find_all('table', class_='table-bordered')
            
            for table in tables:
                rows = table.find_all('tr')
                jenis = None
                
                # Look for the "Jenis" row
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        if cells[0].get_text(strip=True) == "Jenis":
                            jenis = cells[1].get_text(strip=True)
                            break
                
                # Check if this is one of the requested document types
                if jenis in document_types:
                    # Find the parent structure to locate the download link
                    parent = table.find_parent('div', class_='col-md-6')
                    if parent:
                        download_link = parent.find('a', href=re.compile(r'_upload/DOKUMEN'))
                        
                        if download_link:
                            return self.download_document(download_link, package, jenis)
            
            return False
            
        except Exception as e:
            self._increment_error()
            self.update_status(f"Error checking package {package['nomor']}: {e}", "error")
            return False
    
    def download_document(self, download_link, package, document_type):
        """Download a document."""
        try:
            pdf_url = download_link.get('href')
            
            # Make URL absolute if needed
            if not pdf_url.startswith('http'):
                pdf_url = f"{self.base_url}{pdf_url}" if pdf_url.startswith('/') else f"{self.base_url}/{pdf_url}"
            
            # Create folder for document type
            download_folder = f"{document_type.replace(' ', '_')}_Downloads"
            if not os.path.exists(download_folder):
                os.makedirs(download_folder)
            
            # Extract filename
            filename = pdf_url.split('/')[-1]
            filepath = os.path.join(download_folder, filename)
            
            # Check if already downloaded
            if os.path.exists(filepath):
                self._increment_skipped()
                self.update_status(f"Already exists: {filename}", "info")
                return True
            else:
                # Download the file
                self.update_status(f"Downloading: {filename}", "info")
                
                pdf_response = requests.get(pdf_url, stream=True)
                if pdf_response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        for chunk in pdf_response.iter_content(chunk_size=8192):
                            if self.should_stop:
                                break
                            f.write(chunk)
                    
                    if not self.should_stop:
                        self._increment_downloaded()
                        self.update_status(f"✓ Saved: {filename}", "success")
                        return True
                else:
                    self._increment_error()
                    self.update_status(f"Failed to download (HTTP {pdf_response.status_code})", "error")
                    
        except Exception as e:
            self._increment_error()
            self.update_status(f"Download error: {e}", "error")
        
        return False
    
    def _process_package(self, package, document_types, total_packages):
        """Process a single package - wrapper for concurrent execution."""
        if self.should_stop:
            return None
        
        try:
            result = self.check_package_documents(package, document_types)
            processed = self._increment_processed()
            self.update_progress(processed, total_packages, 
                               f"Processed: {package['nomor']} - {package['nama']}")
            return result
        except Exception as e:
            self._increment_error()
            self.update_status(f"Error processing {package['nomor']}: {e}", "error")
            return False
    
    def bulk_download(self, document_types, session_cookie):
        """Start bulk download with specified document types using concurrent workers."""
        self.is_downloading = True
        self.should_stop = False
        
        # Reset counters
        self.downloaded_files = 0
        self.skipped_files = 0
        self.error_count = 0
        self.processed_count = 0
        
        try:
            # Set session cookie
            self.set_session_cookie(session_cookie)
            
            # Get all packages
            all_packages_data = self.get_packages()
            if not all_packages_data:
                return {"success": False, "error": "No packages found"}
            
            # Parse packages
            packages = []
            for row in all_packages_data:
                package = self.parse_package(row)
                if package:
                    packages.append(package)
            
            if not packages:
                return {"success": False, "error": "No valid packages found"}
            
            total_packages = len(packages)
            
            # Start concurrent download process
            self.update_status(f"Starting concurrent download for {total_packages} packages...")
            self.update_status(f"Document types: {', '.join(document_types)}")
            self.update_status(f"Using {self.max_workers} concurrent workers")
            
            # Use ThreadPoolExecutor for concurrent downloads
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all packages for processing
                futures = {
                    executor.submit(self._process_package, pkg, document_types, total_packages): pkg 
                    for pkg in packages
                }
                
                # Process completed futures
                for future in as_completed(futures):
                    if self.should_stop:
                        self.update_status("Stopping workers...", "warning")
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    
                    # Exceptions are handled within _process_package
                    try:
                        future.result()
                    except Exception as e:
                        self._increment_error()
                        self.update_status(f"Worker error: {e}", "error")
            
            # Final summary
            if self.should_stop:
                self.update_status("Download stopped by user", "warning")
            else:
                self.update_status("Download completed!")
            
            self.update_status(f"Summary: {self.downloaded_files} downloaded, {self.skipped_files} skipped, {self.error_count} errors")
            
            return {
                "success": True,
                "downloaded": self.downloaded_files,
                "skipped": self.skipped_files,
                "errors": self.error_count,
                "total_packages": total_packages
            }
            
        except Exception as e:
            self.update_status(f"Download failed: {e}", "error")
            return {"success": False, "error": str(e)}
        finally:
            self.is_downloading = False

# Test function
if __name__ == "__main__":
    def progress_callback(current, total, percentage, message):
        print(f"Progress: {current}/{total} ({percentage:.1f}%) - {message}")
    
    def status_callback(message, level):
        print(f"[{level.upper()}] {message}")
    
    downloader = EnhancedDownloader()
    downloader.set_callbacks(progress_callback, status_callback)
    
    # Test with user input
    session_cookie = input("Enter session cookie: ").strip()
    if session_cookie:
        result = downloader.bulk_download(["AKTE KEMATIAN"], session_cookie)
        print(f"Download result: {result}")
