from flask import Flask, render_template, request, jsonify
import yt_dlp
import os
import re

app = Flask(__name__)

download_progress = {"percent": "0", "speed": "0 KB/s", "size": "Calculating...", "status": "Waiting..."}

def progress_hook(d):
    global download_progress
    if d['status'] == 'downloading':
        p_str = d.get('_percent_str', '0%')
        s_str = d.get('_speed_str', '0 KB/s')
        t_size = d.get('_total_bytes_str') or d.get('_total_bytes_estimate_str') or 'Unknown'
        
        p_clean = re.sub(r'\x1b\[[0-9;]*m', '', p_str).replace('%', '').strip()
        s_clean = re.sub(r'\x1b\[[0-9;]*m', '', s_str).strip()
        size_clean = re.sub(r'\x1b\[[0-9;]*m', '', t_size).strip()
        
        download_progress["percent"] = p_clean
        download_progress["speed"] = s_clean
        download_progress["size"] = size_clean
        download_progress["status"] = "DOWNLOADING DATA..."
        
    elif d['status'] == 'finished':
        download_progress["status"] = "MERGING AUDIO & VIDEO..."

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get_formats', methods=['POST'])
def get_formats():
    url = request.json.get('url')
    try:
        with yt_dlp.YoutubeDL({'nocolor': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = []
            seen_res = set()
            
            for f in info['formats']:
                if f.get('vcodec') != 'none' and f.get('acodec') == 'none':
                    height = f.get('height')
                    if not height: continue
                    
                    # Premium Quality Naming
                    if height >= 4320: res_name = '8K'
                    elif height >= 2160: res_name = '4K'
                    elif height >= 1440: res_name = '2K'
                    elif height >= 1080: res_name = '1080p'
                    elif height >= 720: res_name = '720p'
                    elif height >= 480: res_name = '480p'
                    elif height >= 360: res_name = '360p'
                    elif height >= 240: res_name = '240p'
                    else: res_name = '144p'
                    
                    if res_name not in seen_res:
                        seen_res.add(res_name)
                        
                        # Real Size Calculation in MB/GB
                        size_bytes = f.get('filesize') or f.get('filesize_approx') or 0
                        if size_bytes > 0:
                            if size_bytes >= 1024**3:
                                size_str = f"{size_bytes / (1024**3):.2f} GB"
                            else:
                                size_str = f"{size_bytes / (1024**2):.2f} MB"
                        else:
                            size_str = "Size Unknown"
                            
                        formats.append({
                            'format_id': f['format_id'],
                            'resolution': res_name,
                            'size': size_str,
                            'height': height
                        })
            
            # Sort qualities from Highest to Lowest
            formats = sorted(formats, key=lambda x: x['height'], reverse=True)
            return jsonify({'status': 'success', 'title': info.get('title'), 'thumbnail': info.get('thumbnail'), 'formats': formats})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/progress')
def progress():
    return jsonify(download_progress)

@app.route('/download', methods=['POST'])
def download():
    global download_progress
    download_progress = {"percent": "0", "speed": "0 KB/s", "size": "Calculating...", "status": "STARTING..."}
    data = request.json
    url, format_id = data.get('url'), data.get('format_id')
    
    path = os.path.join(os.path.expanduser('~'), 'Downloads', 'Adixo_Down')
    if not os.path.exists(path): 
        os.makedirs(path)

    ydl_opts = {
        'format': f'{format_id}+bestaudio/best',
        'merge_output_format': 'mp4',
        'outtmpl': os.path.join(path, '%(title)s.%(ext)s'),
        'progress_hooks': [progress_hook],
        'nocolor': True,
        'concurrent_fragment_downloads': 10
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        download_progress["status"] = "Finished"
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=False, port=5000, threaded=True)