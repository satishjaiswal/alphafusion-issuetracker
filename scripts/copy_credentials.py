#!/usr/bin/env python3
"""
Copy sensitive credentials from mounted .credentials volume to container filesystem.

This script reads config_mapping.json to determine which keys are sensitive,
then copies the corresponding credential files from the mounted volume to
the container filesystem so SecureConfigLoader can access them.
"""

import json
import shutil
import sys
from pathlib import Path
import fnmatch

def copy_sensitive_credentials(config_mapping_file: Path, source_credentials_dir: Path, target_credentials_dir: Path):
    """
    Copy sensitive credentials based on config mapping.
    
    Args:
        config_mapping_file: Path to config_mapping.json
        source_credentials_dir: Source directory (mounted volume)
        target_credentials_dir: Target directory (container filesystem)
    """
    # Load config mapping
    with open(config_mapping_file, 'r') as f:
        config_mapping = json.load(f)
    
    sensitive_patterns = config_mapping.get('sensitive_keys', [])
    non_sensitive_patterns = config_mapping.get('non_sensitive_keys', [])
    
    # Sort patterns by length (longest first) for most specific match
    sensitive_patterns.sort(key=len, reverse=True)
    non_sensitive_patterns.sort(key=len, reverse=True)
    
    def is_sensitive(key: str) -> bool:
        """Check if a key is sensitive"""
        # Check sensitive patterns first
        for pattern in sensitive_patterns:
            if fnmatch.fnmatch(key, pattern):
                # Check if overridden by non-sensitive pattern
                for non_pattern in non_sensitive_patterns:
                    if fnmatch.fnmatch(key, non_pattern):
                        return False
                return True
        return False
    
    # Find all credential files in source directory
    copied_count = 0
    
    # Always copy integrations/firebase.json and app/issuetracker/*.json (Google OAuth)
    files_to_copy = [
        'integrations/firebase.json',
        'integrations/firebase-admin.json',
        'app/issuetracker/google-issuetracker.json',
    ]
    
    for file_path in files_to_copy:
        source_file = source_credentials_dir / file_path
        if source_file.exists():
            target_file = target_credentials_dir / file_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, target_file)
            print(f"Copied: {file_path}")
            copied_count += 1
    
    # Also copy any other files that match sensitive patterns
    for cred_file in source_credentials_dir.rglob('*.json'):
        if not cred_file.is_file():
            continue
        
        # Get relative path from source credentials dir
        try:
            rel_path = cred_file.relative_to(source_credentials_dir)
        except ValueError:
            continue
        
        # Skip if already copied
        if str(rel_path) in files_to_copy:
            continue
        
        # Convert file path to config key format
        # e.g., integrations/firebase.json -> integrations/firebase/*
        parts = rel_path.parts
        if len(parts) < 2:
            continue
        
        # Check all possible keys in this file
        category_path = '/'.join(parts[:-1])
        file_key_base = parts[-1].replace('.json', '')
        
        # Check if any key in this file is sensitive
        keys_to_check = [
            f"{category_path}/{file_key_base}",
            f"{category_path}/*",
        ]
        
        should_copy = False
        for key_pattern in keys_to_check:
            if is_sensitive(key_pattern):
                should_copy = True
                break
        
        if should_copy:
            # Copy file to target directory
            target_file = target_credentials_dir / rel_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(cred_file, target_file)
            print(f"Copied: {rel_path}")
            copied_count += 1
    
    print(f"Copied {copied_count} credential file(s)")
    return copied_count

if __name__ == '__main__':
    config_mapping = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/app/alphafusion-issuetracker/config_mapping.json')
    source_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('/app/.credentials')
    target_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else Path('/app/.credentials')
    
    if not config_mapping.exists():
        print(f"Config mapping file not found: {config_mapping}")
        sys.exit(1)
    
    if not source_dir.exists():
        print(f"Source credentials directory not found: {source_dir}")
        sys.exit(1)
    
    target_dir.mkdir(parents=True, exist_ok=True)
    
    copy_sensitive_credentials(config_mapping, source_dir, target_dir)

