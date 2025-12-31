#!/usr/bin/env python3
"""
Session validation utility for E-Paket system.
Validates if the provided session cookie is working.
"""

import requests
import re

class SessionValidator:
    def __init__(self, base_url="http://real-base-url-is.hidden"): # Contact the developer for the real base url
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.5",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{base_url}/pengajuan"
        })
    
    def validate_session(self, session_cookie):
        """Validate the session cookie by testing API connectivity."""
        try:
            # Clean and set the session cookie
            if "ci_session=" not in session_cookie:
                session_cookie = f"ci_session={session_cookie}"
            
            self.session.headers["Cookie"] = session_cookie
            
            # Test the API endpoint
            response = self.session.get(f"{self.base_url}/pengajuan/data_pengajuan_ajax")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "data" in data and isinstance(data["data"], list):
                        return True, f"✓ Session valid - Found {len(data['data'])} packages"
                    else:
                        return False, "✗ Invalid session - No data received"
                except:
                    return False, "✗ Invalid session - Unexpected response format"
            elif response.status_code == 401:
                return False, "✗ Session expired - Please login again"
            elif response.status_code == 403:
                return False, "✗ Access forbidden - Check permissions"
            else:
                return False, f"✗ HTTP {response.status_code} - Server error"
                
        except requests.exceptions.ConnectionError:
            return False, "✗ Connection failed - Check network/server"
        except requests.exceptions.Timeout:
            return False, "✗ Timeout - Server not responding"
        except Exception as e:
            return False, f"✗ Error: {str(e)}"
    
    def test_document_api(self, session_cookie, document_type="AKTE KEMATIAN"):
        """Test document API with a specific document type."""
        try:
            if "ci_session=" not in session_cookie:
                session_cookie = f"ci_session={session_cookie}"
            
            self.session.headers["Cookie"] = session_cookie
            
            # First get packages
            response = self.session.get(f"{self.base_url}/pengajuan/data_pengajuan_ajax")
            if response.status_code != 200:
                return False, "Cannot fetch packages"
            
            packages_data = response.json()
            all_packages = packages_data.get("data", [])
            
            if not all_packages:
                return False, "No packages found"
            
            # Test with first package
            test_package = all_packages[0]
            link_html = test_package[1]
            
            # Extract package info
            link_match = re.search(r'href="pengajuan/lihat_paket/([^"]+)"[^>]*>([^<]+)</a>', link_html)
            if not link_match:
                return False, "Cannot parse package data"
            
            kode_paket_encoded = link_match.group(1)
            nomor_paket = link_match.group(2)
            nama = test_package[3]
            
            # Test document API
            response = self.session.post(
                f"{self.base_url}/pengajuan/dokumencetak",
                data={
                    "kode_paket": kode_paket_encoded,
                    "nomor": nomor_paket,
                    "nama": nama
                }
            )
            
            if response.status_code == 200:
                return True, "Document API working"
            else:
                return False, f"Document API failed (HTTP {response.status_code})"
                
        except Exception as e:
            return False, f"Document API error: {str(e)}"

if __name__ == "__main__":
    # Test the validator
    validator = SessionValidator()
    
    print("Session Validator Test")
    print("=" * 50)
    
    # Test with sample cookie (you'll need to provide a real one)
    test_cookie = input("Enter your session cookie: ").strip()
    
    if test_cookie:
        is_valid, message = validator.validate_session(test_cookie)
        print(f"Validation result: {message}")
        
        if is_valid:
            is_working, doc_message = validator.test_document_api(test_cookie)
            print(f"Document API test: {doc_message}")
