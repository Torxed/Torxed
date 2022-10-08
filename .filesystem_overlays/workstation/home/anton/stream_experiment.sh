#!/bin/bash

ffmpeg -re \
    -thread_queue_size 1024 \
                -f alsa \
                -filter_complex "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo" \
                -ac 2 \
                -i pipewire \
    -thread_queue_size 1024 \
                -video_size 1920x1080 \
                -framerate 60 \
                -f x11grab -i :0.0 \
                -codec:v libx264 \
                -preset ultrafast \
                -tune zerolatency \
                -crf 10 \
                -b:v 6M \
                -maxrate 16M \
                -minrate 8M \
                -bufsize 8M \
                -color_range 2 \
                -bsf:v h264_mp4toannexb \
        -f rtsp -muxdelay 0.1 rtsp://127.0.0.1:5545/abc
