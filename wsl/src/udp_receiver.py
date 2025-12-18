"""
UDP Receiver Module for WSL Server
Handles receiving and reconstructing frame packages from RPi
"""

import socket
import struct
import time
import threading
import logging
import pickle
import zlib
from typing import Optional, Dict, Callable
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FrameAssembler:
    """
    Assembles fragmented frames from UDP packets
    """
    
    def __init__(self, timeout: float = 2.0, callback: Optional[Callable] = None):
        """
        Initialize frame assembler
        
        Args:
            timeout: Time to wait for missing chunks before discarding
            callback: Function to call when frame is complete (receives package dict)
        """
        self.timeout = timeout
        self.frame_callback = callback
        self.frames = defaultdict(lambda: {
            'chunks': {},
            'total_chunks': 0,
            'first_seen': 0,
            'complete': False
        })
        self.lock = threading.Lock()
        
        # Statistics
        self.total_frames_received = 0
        self.total_frames_dropped = 0
        self.total_chunks_received = 0
    
    def add_chunk(self, frame_id: int, chunk_id: int, total_chunks: int, chunk_data: bytes):
        """
        Add a chunk to the assembler
        
        Args:
            frame_id: ID of the frame
            chunk_id: ID of this chunk
            total_chunks: Total number of chunks for this frame
            chunk_data: Chunk data
        """
        current_time = time.time()
        
        frame = self.frames[frame_id]
        
        # Initialize frame metadata
        if frame['first_seen'] == 0:
            frame['first_seen'] = current_time
            frame['total_chunks'] = total_chunks
        
        # Store chunk
        frame['chunks'][chunk_id] = chunk_data
        self.total_chunks_received += 1
        
        # Check if frame is complete
        if len(frame['chunks']) == total_chunks:
            self._assemble_frame(frame_id)
    
    def _assemble_frame(self, frame_id: int):
        """
        Assemble complete frame from chunks
        
        Args:
            frame_id: ID of frame to assemble
        """
        frame = self.frames[frame_id]
        
        if frame['complete']:
            return
        
        try:
            # Sort chunks by ID and concatenate
            sorted_chunks = [frame['chunks'][i] for i in sorted(frame['chunks'].keys())]
            assembled_data = b''.join(sorted_chunks)
            
            # Decompress
            decompressed = zlib.decompress(assembled_data)
            
            # Deserialize
            package = pickle.loads(decompressed)
            
            # Add frame ID
            package['frame_id'] = frame_id
            package['assembly_time'] = time.time() - frame['first_seen']
            
            # Call callback with completed frame
            frame['complete'] = True
            self.total_frames_received += 1
            
            # Clean up
            del self.frames[frame_id]
            
            # Invoke callback if set (outside lock for better performance)
            if self.frame_callback:
                try:
                    self.frame_callback(package)
                except Exception as e:
                    logger.error(f"Error in frame callback: {e}")
                    self.total_frames_dropped += 1
            else:
                logger.warning(f"No callback set, frame {frame_id} assembled but not processed")
                
        except Exception as e:
            logger.error(f"Error assembling frame {frame_id}: {e}")
            self.total_frames_dropped += 1
    
    def cleanup_old_frames(self):
        """
        Remove incomplete frames that have timed out
        """
        current_time = time.time()
        expired_frames = []
        
        for frame_id, frame in self.frames.items():
            if not frame['complete'] and (current_time - frame['first_seen']) > self.timeout:
                expired_frames.append(frame_id)
        
        for frame_id in expired_frames:
            logger.warning(f"Frame {frame_id} timed out "
                          f"({len(self.frames[frame_id]['chunks'])}/{self.frames[frame_id]['total_chunks']} chunks)")
            del self.frames[frame_id]
            self.total_frames_dropped += 1
    
    def get_stats(self) -> dict:
        """
        Get assembler statistics
        
        Returns:
            dict: Statistics
        """
        return {
            'frames_received': self.total_frames_received,
            'frames_dropped': self.total_frames_dropped,
            'chunks_received': self.total_chunks_received,
            'pending_frames': len(self.frames)
        }


class UDPReceiver:
    """
    UDP server for receiving frame streams from RPi
    """
    
    def __init__(self, config: dict):
        """
        Initialize UDP receiver
        
        Args:
            config: Network configuration
        """
        self.config = config
        self.network_config = config.get('network', {})
        
        # Network parameters
        self.listen_host = self.network_config.get('listen_host', '0.0.0.0')
        self.listen_port = self.network_config.get('listen_port', 5000)
        self.buffer_size = self.network_config.get('buffer_size', 65536)
        
        # Socket
        self.sock = None
        self.running = False
        
        # Frame assembler with callback
        self.assembler = FrameAssembler(timeout=2.0, callback=self._handle_completed_frame)
        
        # Receiver thread
        self.receive_thread = None
        self.cleanup_thread = None
        
        # Frame buffer for external access (optional)
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        
        # Statistics
        self.packets_received = 0
        self.bytes_received = 0
        self.last_packet_time = 0
        
        logger.info(f"UDPReceiver initialized: {self.listen_host}:{self.listen_port}")
    
    def start(self) -> bool:
        """
        Start UDP receiver
        
        Returns:
            bool: True if started successfully
        """
        try:
            # Create socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024)  # 1MB buffer
            self.sock.bind((self.listen_host, self.listen_port))
            self.sock.settimeout(1.0)
            
            self.running = True
            
            # Start receiver thread
            self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.receive_thread.start()
            
            # Start cleanup thread
            self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
            self.cleanup_thread.start()
            
            logger.info(f"UDP receiver started on {self.listen_host}:{self.listen_port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start UDP receiver: {e}")
            return False
    
    def stop(self):
        """
        Stop UDP receiver
        """
        logger.info("Stopping UDP receiver...")
        self.running = False
        
        if self.receive_thread:
            self.receive_thread.join(timeout=2.0)
        
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=2.0)
        
        if self.sock:
            self.sock.close()
            self.sock = None
        
        logger.info("UDP receiver stopped")
    
    def _receive_loop(self):
        """
        Main receive loop
        """
        logger.info("Starting receive loop...")
        
        while self.running:
            try:
                # Receive packet
                data, addr = self.sock.recvfrom(self.buffer_size)
                
                if not data:
                    continue
                
                self.packets_received += 1
                self.bytes_received += len(data)
                self.last_packet_time = time.time()
                
                # Parse packet header
                packet_type = struct.unpack('B', data[0:1])[0]
                
                if packet_type == 0:
                    # Control packet
                    self._handle_control_packet(data[13:], addr)
                elif packet_type == 1:
                    # Data packet
                    self._handle_data_packet(data[1:], addr)
                else:
                    logger.warning(f"Unknown packet type: {packet_type}")
                
                # Log statistics periodically
                if self.packets_received % 1000 == 0:
                    logger.info(f"Received {self.packets_received} packets, "
                              f"{self.bytes_received / (1024**2):.2f} MB total")
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Error in receive loop: {e}")
    
    def _handle_control_packet(self, data: bytes, addr: tuple):
        """
        Handle control packet
        
        Args:
            data: Packet data
            addr: Sender address
        """
        message = data.decode('utf-8', errors='ignore')
        logger.info(f"Control packet from {addr}: {message}")
    
    def _handle_data_packet(self, data: bytes, addr: tuple):
        """
        Handle data packet
        
        Args:
            data: Packet data
            addr: Sender address
        """
        try:
            # Parse packet header: timestamp(8) + data_length(4)
            timestamp = struct.unpack('d', data[0:8])[0]
            data_length = struct.unpack('I', data[8:12])[0]
            
            # Parse chunk header: frame_id(8) + chunk_id(4) + total_chunks(4)
            frame_id = struct.unpack('Q', data[12:20])[0]
            chunk_id = struct.unpack('I', data[20:24])[0]
            total_chunks = struct.unpack('I', data[24:28])[0]
            
            # Extract chunk data
            chunk_data = data[28:28 + data_length]
            
            # Add to assembler
            self.assembler.add_chunk(frame_id, chunk_id, total_chunks, chunk_data)
            
        except Exception as e:
            logger.error(f"Error handling data packet: {e}")
    
    def _cleanup_loop(self):
        """
        Periodic cleanup of old incomplete frames
        """
        while self.running:
            try:
                self.assembler.cleanup_old_frames()
                time.sleep(1.0)
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    def _handle_completed_frame(self, package: dict):
        """
        Handle a completed frame from assembler
        
        Args:
            package: Completed frame package
        """
        with self.frame_lock:
            self.latest_frame = package
        logger.debug(f"Frame {package['frame_id']} ready, assembly time: {package['assembly_time']*1000:.1f}ms")
    
    def get_frame(self, timeout: float = 1.0) -> Optional[dict]:
        """
        Get latest received frame (non-blocking)
        Note: Returns the most recent frame and clears it
        
        Args:
            timeout: Not used (kept for API compatibility)
            
        Returns:
            dict: Frame package or None
        """
        with self.frame_lock:
            frame = self.latest_frame
            self.latest_frame = None
            return frame
    
    def get_stats(self) -> dict:
        """
        Get receiver statistics
        
        Returns:
            dict: Statistics dictionary
        """
        assembler_stats = self.assembler.get_stats()
        
        return {
            'packets_received': self.packets_received,
            'bytes_received': self.bytes_received,
            'last_packet_time': self.last_packet_time,
            'running': self.running,
            'assembler': assembler_stats
        }


if __name__ == "__main__":
    # Test configuration
    test_config = {
        'network': {
            'listen_host': 'desktop-immdgjc.tail70bfe4.ts.net',
            'listen_port': 5000,
            'buffer_size': 65536
        }
    }
    
    receiver = UDPReceiver(test_config)
    
    if receiver.start():
        try:
            logger.info("Receiver started, waiting for frames...")
            
            while True:
                time.sleep(1.0)  # Check every second
                frame = receiver.get_frame()
                if frame:
                    logger.info(f"Received frame {frame['frame_id']}, "
                              f"assembly time: {frame['assembly_time']*1000:.1f}ms")
                    logger.info(f"Stats: {receiver.get_stats()}")
                else:
                    # Just show stats periodically
                    stats = receiver.get_stats()
                    if stats['packets_received'] > 0:
                        logger.info(f"Stats: {stats}")
                    
        except KeyboardInterrupt:
            logger.info("Interrupted")
        finally:
            receiver.stop()
