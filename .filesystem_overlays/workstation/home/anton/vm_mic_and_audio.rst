Installation
============

This reminder-note assumes:

* `Arch Linux` host OS has an IP of `172.22.0.80`
* `Windows` VM has an IP of `172.22.0.81`
* The microphone is on the host OS
* The audio output you want to play back is sent from the VM to the host OS

On the host
-----------

* :code:`pacman -S pipewire pipewire-alsa`
* :code:`yay -S vban-git` which installs the `vban`_ github repo

On the network client (windows)
-------------------------------

Install `Voice Meeter Banana`_ and `VB-Cable`_

Configuration
=============

Host
====

It should be enough to just have :code:`vban-git` installed really.

.. Setup a virtual mixed source 
.. And set up a virtual microphone

.. pactl load-module module-null-sink media.class=Audio/Sink sink_name=my-combined-sink channel_map=stereo
.. pactl load-module module-null-sink media.class=Audio/Source/Virtual sink_name=my-virtualmic channel_map=front-left,front-right

.. Courtesy of https://youtu.be/Goeucg7A9qE and https://superuser.com/questions/1675877/how-to-create-a-new-pipewire-virtual-device-that-to-combines-an-real-input-and-o

Client
------

In Voice Meeter, select :code:`A1` and :code:`KS: Scream`.
Press the :code:`VBAN` icon and create/modify:

* :code:`Incoming` should have a Stream Name :code:`Stream1 IP` with IP address from :code:`172.22.0.80`
* :code:`Outgoing` to the same IP and name but the :code:`Net Quality` should be set to :code:`Fast`.

:warning: Make sure :code:`Stream Name` matches between :code:`Voice Meeter`'s :code:`VBAN` options and :code:`vban_receptor` + :code:`vban_emitter` on the host OS.

Then press :code:`On` on both of them.

Running
=======

Host
----

Run:

* :code:`vban_receptor --ipaddress=172.22.0.81 --port 6980 --streamname windows`
* :code:`vban_emitter --ipaddress=172.22.0.81 --port=6980 --streamname=Stream1`

Client
------

Press :code:`VBAN is OFF` so it turns on, after which VBAN should be emitting on port :code:`6980` by default, you'll see the port in the top header of :code:`VBAN` options in `Voice Meeter Banana`_.

.. _`Voice Meeter Banana`: https://vb-audio.com/Voicemeeter/banana.htm
.. _`VB-Cable`: https://vb-audio.com/Cable/index.htm
.. _`vban`: https://github.com/quiniouben/vban/
