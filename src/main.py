 #* Core networking
import socket
import asyncio
import struct  # for binary protocol design
import threading
import multiprocessing
#* Protocol design
import json  # or design your own serialization
import pickle  # Python object serialization
import msgpack  # efficient binary serialization
import protobuf  # if you want structured messages