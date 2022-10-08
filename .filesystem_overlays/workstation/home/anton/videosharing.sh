xrandr --output DisplayPort-0 --mode 1920x1080

perl /usr/share/perl5/site_perl/RTSP/rtsp-server.pl --clientport 5546

# At some point, use a screen area grabber to share just a section of the screen instead :)
# Also the compression isn't perfect because it resets the compression every X seconds
ffmpeg -re \
        -f alsa \
                -filter_complex "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo" \
                -ac 2 \
                -i pipewire \
        -video_size 1920x1080 -framerate 60 -f x11grab -i :0.0+2560+0 \
                -codec:v libx264 \
                -preset fast \
                -tune zerolatency \
                -color_range 2 \
                -crf 10 \
                -bsf:v h264_mp4toannexb \
        -maxrate 9M \
        -minrate 1M \
        -bufsize 2M \
        -f rtsp -muxdelay 0.1 rtsp://127.0.0.1:5545/abc

vlc rtsp://127.0.0.1:5546/abc
