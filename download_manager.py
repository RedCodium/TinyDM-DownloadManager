import os
import json
import requests
from threading import Thread
from urllib.parse import urlparse

class DownloadManager:
    def __init__(self, save_dir="downloads"):
        self.save_dir = save_dir
        self.downloads = {}
        self.state_file = "download_state.json"
        os.makedirs(save_dir, exist_ok=True)
        self.load_state()

    def add_download(self, url):
        """Add a new download task."""
        filename = os.path.basename(urlparse(url).path)
        if not filename:
            filename = "download_" + url.split('/')[-1]
        
        download_path = os.path.join(self.save_dir, filename)
        download_id = len(self.downloads)
        
        self.downloads[download_id] = {
            'url': url,
            'filename': filename,
            'path': download_path,
            'total_size': 0,
            'downloaded': 0,
            'status': 'pending',
            'thread': None
        }
        
        return download_id

    def start_download(self, download_id, callback=None):
        """Start or resume a download."""
        if download_id not in self.downloads:
            return False
        
        download = self.downloads[download_id]
        if download['status'] in ['downloading', 'completed']:
            return False

        headers = {}
        if os.path.exists(download['path']):
            download['downloaded'] = os.path.getsize(download['path'])
            headers['Range'] = f'bytes={download["downloaded"]}-'

        def download_thread():
            try:
                response = requests.get(download['url'], headers=headers, stream=True)
                
                if 'content-length' in response.headers:
                    download['total_size'] = int(response.headers['content-length'])
                    if 'Range' in headers:
                        download['total_size'] += download['downloaded']

                mode = 'ab' if download['downloaded'] > 0 else 'wb'
                download['status'] = 'downloading'
                
                with open(download['path'], mode) as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if download['status'] == 'paused':
                            self.save_state()
                            return
                        if chunk:
                            f.write(chunk)
                            download['downloaded'] += len(chunk)
                            if callback:
                                callback(download_id, download)

                download['status'] = 'completed'
                if callback:
                    callback(download_id, download)
                self.save_state()

            except Exception as e:
                download['status'] = 'error'
                download['error'] = str(e)
                if callback:
                    callback(download_id, download)
                self.save_state()

        download['thread'] = Thread(target=download_thread)
        download['thread'].start()
        return True

    def pause_download(self, download_id):
        """Pause a download."""
        if download_id in self.downloads:
            self.downloads[download_id]['status'] = 'paused'
            self.save_state()
            return True
        return False

    def get_download_info(self, download_id):
        """Get information about a download."""
        return self.downloads.get(download_id)

    def save_state(self):
        """Save the current state of downloads."""
        state = {
            id_: {
                k: v for k, v in download.items()
                if k != 'thread'
            }
            for id_, download in self.downloads.items()
        }
        with open(self.state_file, 'w') as f:
            json.dump(state, f)

    def load_state(self):
        """Load the previous state of downloads."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                for id_, download in state.items():
                    download['thread'] = None
                    self.downloads[int(id_)] = download
            except:
                pass