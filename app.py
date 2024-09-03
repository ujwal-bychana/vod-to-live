from flask import Flask, send_from_directory, abort
import os
import m3u8
import time

app = Flask(__name__)

CURR_PATH = None
LAST_SEGMENT = {}
MEDIA_SEQUENCE = {}
VARIANTS = {}
LAST_PLAYLIST = {}
LAST_REQUEST_TIMESTAMP = {}
REPEAT = False


def initialize():
    print("initialize")
    global CURR_PATH, VARIANTS, LAST_PLAYLIST, LAST_REQUEST_TIMESTAMP
    CURR_PATH = os.getcwd()
    variantsList = []
    for root, dirs, files in os.walk(CURR_PATH + '/media'):
        for file in files:
            if file.endswith(".m3u8"):
                variantsList.append(file)
    for variant in variantsList:
        fileContents = ''
        with open(os.path.abspath(os.path.join(CURR_PATH + '/media/', variant)), 'r') as file:
            fileContents = file.read()
            VARIANTS[variant] = m3u8.loads(fileContents)
            LAST_SEGMENT[variant] = 0
            MEDIA_SEQUENCE[variant] = 1
            LAST_PLAYLIST[variant] = VARIANTS[variant].segments[0:15]
            LAST_REQUEST_TIMESTAMP[variant] = 0
            # LAST_PLAYLIST[variant] = VARIANTS[variant].segments #for time based

initialize()

def generatePlaylist(segmentsList, filename):
    newPlaylist = m3u8.M3U8()
    newSegmentsList = LAST_PLAYLIST[filename]
    for i in range(len(segmentsList)):
        segment = newSegmentsList[i]
        newPlaylist.add_segment(segment)
    newPlaylist.version = 6
    newPlaylist.is_endlist = False
    newPlaylist.target_duration = VARIANTS[filename].target_duration
    newPlaylist.media_sequence = MEDIA_SEQUENCE[filename]
    LAST_PLAYLIST[filename] = newPlaylist.segments
    return newPlaylist.dumps()
    
@app.route('/hls/<path:filename>', methods=['GET'])
def hls(filename):
    try:
        global LAST_SEGMENT, MEDIA_SEQUENCE, LAST_PLAYLIST, REPEAT, LAST_REQUEST_TIMESTAMP
        currTime = int(time.time())
        if filename.endswith('.m3u8') and len(VARIANTS[filename].segments) != 0 and (currTime - LAST_REQUEST_TIMESTAMP[filename]) < 4: #4 is the Target duration
            return generatePlaylist(LAST_PLAYLIST[filename], filename)
        file_path = os.path.abspath(os.path.join(CURR_PATH + '/media', filename))
        if not file_path.startswith(os.path.abspath(CURR_PATH + '/media')):
            abort(404)
        if filename.endswith('.m3u8') and len(VARIANTS[filename].segments) != 0:
            cond = len(VARIANTS[filename].segments) - 15 if not REPEAT else len(VARIANTS[filename].segments)
            if(LAST_SEGMENT[filename]+1 > cond):
                return generatePlaylist(LAST_PLAYLIST[filename], filename)
            else:
                segmentsList = LAST_PLAYLIST[filename]
                index = len(LAST_PLAYLIST[filename]) + LAST_SEGMENT[filename] if not REPEAT else LAST_SEGMENT[filename]
                segmentsList.append(VARIANTS[filename].segments[index])
                LAST_SEGMENT[filename] += 1
                MEDIA_SEQUENCE[filename] += 1
            newPlaylist = m3u8.M3U8()
            newSegmentsList = segmentsList[-15:]
            for i in range(len(newSegmentsList)):
                segment = newSegmentsList[i]
                if REPEAT and LAST_SEGMENT[filename] == 1 and i == len(newSegmentsList) - 1:
                    segment.discontinuity = True
                newPlaylist.add_segment(segment)
            newPlaylist.version = 6
            newPlaylist.is_endlist = False
            newPlaylist.target_duration = VARIANTS[filename].target_duration
            newPlaylist.media_sequence = MEDIA_SEQUENCE[filename]
            LAST_PLAYLIST[filename] = newPlaylist.segments
            LAST_REQUEST_TIMESTAMP[filename] = int(time.time())
            return newPlaylist.dumps()
        else:
            return send_from_directory(CURR_PATH + '/media', filename)
    except FileNotFoundError:
        abort(404)


if __name__ == '__main__':
    initialize()
    app.run(debug=True)
