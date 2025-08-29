    def _copy_by_mmap_windows(self, source_path: str, temp_path: str, file_size: int) -> dict:
        """
        DIRECT-LARGE: Fixed Windows pre-allocation using direct API calls
        """
        try:
            self._log_status(f"Pre-allocating temp file '{temp_path}' to {file_size:,} bytes (Win32 direct)")
            log_and_flush(logging.INFO, f"Start Pre-allocate temp file '{temp_path}' to {file_size:,} bytes (Win32 direct)")
            
            # Diagnostic: Volume info
            try:
                drive_root = os.path.splitdrive(temp_path)[0] + '\\'
                vol_name_buf = ctypes.create_unicode_buffer(260)
                fs_name_buf = ctypes.create_unicode_buffer(260)
                serial = ctypes.c_uint32(0)
                max_comp = ctypes.c_uint32(0)
                fs_flags = ctypes.c_uint32(0)
                
                ok = kernel32.GetVolumeInformationW(
                    ctypes.c_wchar_p(drive_root),
                    vol_name_buf, ctypes.sizeof(vol_name_buf),
                    ctypes.byref(serial), ctypes.byref(max_comp), ctypes.byref(fs_flags),
                    fs_name_buf, ctypes.sizeof(fs_name_buf)
                )
                
                if ok:
                    log_and_flush(logging.DEBUG, 
                        f"Volume info: drive='{drive_root}', volume='{vol_name_buf.value}', "
                        f"fs='{fs_name_buf.value}', flags=0x{fs_flags.value:08X}")
            except Exception as e:
                log_and_flush(logging.DEBUG, f"Volume info diagnostic failed: {e}")
            
            # Create file using direct Windows API with explicit access rights
            preallocation_success = False
            windows_api_used = False
            
            try:
                # Ensure parent directory exists
                Path(temp_path).parent.mkdir(parents=True, exist_ok=True)
                
                # Create file with explicit access rights for allocation
                GENERIC_READ = 0x80000000
                GENERIC_WRITE = 0x40000000
                FILE_WRITE_DATA = 0x0002
                FILE_SHARE_READ = 0x00000001
                FILE_SHARE_WRITE = 0x00000002
                CREATE_ALWAYS = 2  # Creates new file, overwrites if exists
                FILE_ATTRIBUTE_NORMAL = 0x80
                
                # Create file handle with proper access rights
                file_handle = kernel32.CreateFileW(
                    ctypes.c_wchar_p(temp_path),
                    wintypes.DWORD(GENERIC_READ | GENERIC_WRITE | FILE_WRITE_DATA),
                    wintypes.DWORD(FILE_SHARE_READ | FILE_SHARE_WRITE), 
                    None,  # Security attributes
                    wintypes.DWORD(CREATE_ALWAYS),
                    wintypes.DWORD(FILE_ATTRIBUTE_NORMAL),
                    None   # Template file
                )
                
                if file_handle == -1 or file_handle == 0:  # INVALID_HANDLE_VALUE
                    err = kernel32.GetLastError()
                    raise Exception(f"CreateFileW failed: error {err}")
                
                log_and_flush(logging.DEBUG, f"Created file with handle: {file_handle}")
                
                try:
                    # Check for problematic file attributes
                    attrs = kernel32.GetFileAttributesW(ctypes.c_wchar_p(temp_path))
                    if attrs != 0xFFFFFFFF:  # Not INVALID_FILE_ATTRIBUTES
                        if attrs & FILE_ATTRIBUTE_COMPRESSED:
                            raise Exception("File is COMPRESSED - incompatible with SetFileInformationByHandle")
                        if attrs & FILE_ATTRIBUTE_SPARSE_FILE:
                            raise Exception("File is SPARSE - incompatible with SetFileInformationByHandle")
                    
                    # Build FILE_ALLOCATION_INFO with proper LARGE_INTEGER
                    alloc = FILE_ALLOCATION_INFO()
                    alloc.AllocationSize.QuadPart = file_size
                    
                    log_and_flush(logging.DEBUG, f"Setting allocation size to: {file_size:,} bytes")
                    log_and_flush(logging.DEBUG, f"Structure size: {ctypes.sizeof(alloc)} bytes")
                    log_and_flush(logging.DEBUG, f"QuadPart value: {alloc.AllocationSize.QuadPart}")
                    
                    # Try Windows API allocation with better error reporting
                    ok = kernel32.SetFileInformationByHandle(
                        wintypes.HANDLE(file_handle),
                        wintypes.DWORD(FILE_INFO_BY_HANDLE_FileAllocationInfo),
                        ctypes.byref(alloc),
                        wintypes.DWORD(ctypes.sizeof(alloc))
                    )
                    
                    if not ok:
                        err = kernel32.GetLastError()
                        # Get more detailed error info
                        error_details = {
                            5: "ERROR_ACCESS_DENIED - Handle lacks FILE_WRITE_DATA access",
                            87: "ERROR_INVALID_PARAMETER - Invalid parameter to SetFileInformationByHandle",
                            112: "ERROR_DISK_FULL - Insufficient disk space",
                            1224: "ERROR_USER_MAPPED_FILE - File is memory mapped",
                        }
                        error_desc = error_details.get(err, f"Unknown error {err}")
                        raise Exception(f"SetFileInformationByHandle failed: {error_desc}")
                    
                    log_and_flush(logging.DEBUG, "SetFileInformationByHandle succeeded")
                    
                    # Set EOF to make logical size match allocated size  
                    if not kernel32.SetFilePointerEx(wintypes.HANDLE(file_handle), 
                                                   ctypes.c_longlong(file_size), None, 0):
                        err = kernel32.GetLastError()
                        raise Exception(f"SetFilePointerEx failed: error {err}")
                    
                    if not kernel32.SetEndOfFile(wintypes.HANDLE(file_handle)):
                        err = kernel32.GetLastError()
                        raise Exception(f"SetEndOfFile failed: error {err}")
                    
                    preallocation_success = True
                    windows_api_used = True
                    log_and_flush(logging.INFO, f"Windows API pre-allocation successful: {file_size:,} bytes")
                    
                finally:
                    # Always close the handle
                    kernel32.CloseHandle(wintypes.HANDLE(file_handle))
                    
            except Exception as e:
                log_and_flush(logging.WARNING, f"Windows API pre-allocation failed: {e}")
                
                # Fallback to Python truncate
                try:
                    log_and_flush(logging.INFO, "Falling back to Python truncate method")
                    with open(temp_path, 'wb') as tf:
                        tf.truncate(file_size)
                    preallocation_success = True
                    windows_api_used = False
                    log_and_flush(logging.INFO, f"Python truncate successful: {file_size:,} bytes")
                except Exception as e2:
                    raise SystemExit(f"Both Windows API and Python pre-allocation failed: {e2}")
            
            if not preallocation_success:
                raise SystemExit("Pre-allocation failed")
            
            # Log which method was used  
            method = "Windows API (fast)" if windows_api_used else "Python truncate (slower)"
            self._log_status(f"Pre-allocation completed using {method}")
            log_and_flush(logging.INFO, f"Pre-allocation method: {method}")
            
            # Rest of your mmap copying code (unchanged)
            if self.blake3_available:
                hasher = blake3.blake3()
                algo = 'BLAKE3'
            else:
                hasher = hashlib.sha256()
                algo = 'SHA-256'
    
            window = max(1, int(C.FILECOPY_MMAP_WINDOW_BYTES))
            flush_every = max(0, int(C.FILECOPY_MMAP_FLUSH_EVERY_N_WINDOWS))
            bytes_copied = 0
            win_index = 0
    
            with open(source_path, 'rb') as sf, open(temp_path, 'r+b') as tf:
                offset = 0
                total = file_size
                fd = tf.fileno()
                
                while offset < total:
                    # Cancellation checks
                    if getattr(self, 'cancel_event', None) and self.cancel_event.is_set():
                        return {'success': False, 'cancelled': True, 'error': 'Cancelled by user'}
                        
                    pm = getattr(self, 'progress_manager', None)
                    if pm and callable(getattr(pm, 'cancellation_callback', None)) and pm.cancellation_callback():
                        return {'success': False, 'cancelled': True, 'error': 'Cancelled by user'}
    
                    length = min(window, total - offset)
                    try:
                        src_map = mmap.mmap(sf.fileno(), length=length, offset=offset, access=mmap.ACCESS_READ)
                        dst_map = mmap.mmap(fd, length=length, offset=offset, access=mmap.ACCESS_WRITE)
                        
                        try:
                            dst_map[:] = src_map[:]
                            hasher.update(src_map)
                            bytes_copied += length
                        finally:
                            try:
                                dst_map.flush()
                            except Exception:
                                pass
                            dst_map.close()
                            src_map.close()
                            
                    except Exception as e_map:
                        return {'success': False, 'error': f'mmap window failed at offset {offset}: {e_map}'}
    
                    win_index += 1
                    if flush_every and (win_index % flush_every == 0):
                        try:
                            tf.flush()
                            os.fsync(fd)
                        except Exception:
                            pass
    
                    # Progress update
                    if pm and hasattr(pm, 'update_file_progress'):
                        try:
                            pm.update_file_progress(source_path, bytes_copied, total, strategy='DIRECT-LARGE')
                        except Exception:
                            pass
    
                    offset += length
    
                # Final flush
                try:
                    tf.flush()
                    os.fsync(fd)
                except Exception:
                    pass
                    
            log_and_flush(logging.INFO, f"DIRECT-LARGE copy completed: {bytes_copied:,} bytes")
            return {'success': True, 'bytes_copied': bytes_copied, 'hash': hasher.hexdigest(), 'hash_algorithm': algo}
            
        except Exception as e:
            msg = f'DIRECT-LARGE copy failed: {e}'
            log_and_flush(logging.ERROR, msg)
            raise SystemExit(msg)
