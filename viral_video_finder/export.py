import csv
import json
from typing import List
from models import Video

def export_results(videos: List[Video], filename: str, format: str):
    if format == "csv":
        export_to_csv(videos, filename)
    elif format == "json":
        export_to_json(videos, filename)
    else:
        raise ValueError("Unsupported export format. Choose 'csv' or 'json'.")

def export_to_csv(videos: List[Video], filename: str):
    if not videos:
        return

    keys = videos[0].to_dict().keys()
    with open(filename, 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows([video.to_dict() for video in videos])

def export_to_json(videos: List[Video], filename: str):
    with open(filename, 'w', encoding='utf-8') as output_file:
        json.dump([video.to_dict() for video in videos], output_file, ensure_ascii=False, indent=4)
