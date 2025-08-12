import os
import fnmatch
from typing import List, Set, Optional

class FileFilter:
    def __init__(self, max_file_size_mb: Optional[float] = None):
        # None means: no size limit enforced by the backend
        self.max_file_size_bytes = (max_file_size_mb * 1024 * 1024) if (max_file_size_mb is not None) else None
        # Common patterns to exclude from uploads
        self.default_patterns = [
            # Dependencies
            'node_modules/**',
            'venv/**',
            'env/**',
            '.venv/**',
            '.env/**',
            '__pycache__/**',
            '*.pyc',
            '*.pyo',
            '*.pyd',
            '.Python',
            'pip-log.txt',
            'pip-delete-this-directory.txt',
            
            # Build outputs
            'dist/**',
            'build/**',
            '.next/**',
            'out/**',
            'target/**',
            '.output/**',
            '.nuxt/**',
            '.vuepress/dist/**',
            
            # Cache and temp files
            '.cache/**',
            '.tmp/**',
            'tmp/**',
            '*.tmp',
            '*.temp',
            '.sass-cache/**',
            '.parcel-cache/**',
            
            # IDE and editor files
            '.vscode/**',
            '.idea/**',
            '*.swp',
            '*.swo',
            '*~',
            '.project',
            '.classpath',
            '.settings/**',
            '*.sublime-project',
            '*.sublime-workspace',
            
            # OS files
            '.DS_Store',
            '.DS_Store?',
            '._*',
            '.Spotlight-V100',
            '.Trashes',
            'ehthumbs.db',
            'Thumbs.db',
            'desktop.ini',
            
            # Version control
            '.git/**',
            '.svn/**',
            '.hg/**',
            '.bzr/**',
            
            # Logs
            '*.log',
            'logs/**',
            'npm-debug.log*',
            'yarn-debug.log*',
            'yarn-error.log*',
            
            # Runtime data
            'pids/**',
            '*.pid',
            '*.seed',
            '*.pid.lock',
            
            # Coverage directory used by tools like istanbul
            'coverage/**',
            '.nyc_output/**',
            
            # Dependency directories
            'jspm_packages/**',
            'bower_components/**',
            
            # Optional npm cache directory
            '.npm/**',
            
            # Optional eslint cache
            '.eslintcache',
            
            # Large media files
            '*.mp4',
            '*.avi',
            '*.mov',
            '*.mkv',
            '*.iso',
            '*.dmg',
            
            # Archives
            '*.zip',
            '*.tar.gz',
            '*.rar',
            '*.7z',
            '*.tar',
            '*.gz',
            
            # Database files
            '*.db',
            '*.sqlite',
            '*.sqlite3',
            
            # Compiled binaries
            '*.exe',
            '*.dll',
            '*.so',
            '*.dylib',
            
            # Large files (over certain size would be handled separately)
            '*.bin',
            '*.dat'
        ]
    
    def should_exclude(self, file_path: str) -> bool:
        """Check if a file should be excluded based on patterns."""
        # Normalize path separators
        normalized_path = file_path.replace('\\', '/')
        
        for pattern in self.default_patterns:
            if self._match_pattern(normalized_path, pattern):
                return True
        return False
    
    def _match_pattern(self, path: str, pattern: str) -> bool:
        """Match a file path against a gitignore-style pattern."""
        # Handle directory patterns ending with /**
        if pattern.endswith('/**'):
            dir_pattern = pattern[:-3]
            path_parts = path.split('/')
            
            # Check if any part of the path matches the directory pattern
            for i, part in enumerate(path_parts):
                if fnmatch.fnmatch(part, dir_pattern):
                    return True
            
            # Also check if the entire path starts with the directory pattern
            if path.startswith(dir_pattern + '/') or path == dir_pattern:
                return True
        
        # Handle exact file matches (no directory separators in pattern)
        elif '/' not in pattern:
            filename = os.path.basename(path)
            return fnmatch.fnmatch(filename, pattern)
        
        # Handle full path patterns
        else:
            return fnmatch.fnmatch(path, pattern)
        
        return False
    
    def is_file_too_large(self, file_path: str) -> bool:
        """Check if a file is too large based on size limit."""
        # If no limit configured, never exclude by size
        if self.max_file_size_bytes is None:
            return False
        try:
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                return file_size > self.max_file_size_bytes
        except (OSError, IOError):
            # If we can't get file size, assume it's not too large
            pass
        return False
    
    def should_exclude_with_reason(self, file_path: str, actual_file_path: Optional[str] = None) -> tuple[bool, str]:
        """Check if a file should be excluded and return the reason."""
        # Check pattern matching first
        if self.should_exclude(file_path):
            return True, "matches exclusion pattern"
        
        # Check file size if limit is configured and actual file path is provided
        if self.max_file_size_bytes is not None and actual_file_path and self.is_file_too_large(actual_file_path):
            file_size_mb = os.path.getsize(actual_file_path) / (1024 * 1024)
            return True, f"file too large ({file_size_mb:.1f}MB > {self.max_file_size_bytes / (1024 * 1024):.1f}MB)"
        
        return False, ""
    
    def filter_files(self, file_list: List[str]) -> List[str]:
        """Filter a list of file paths, returning only allowed files."""
        return [f for f in file_list if not self.should_exclude(f)]
    
    def filter_files_with_details(self, file_list: List[str], base_path: str = "") -> dict:
        """Filter files and return detailed information about what was excluded."""
        allowed_files = []
        excluded_files = []
        exclusion_reasons = {}
        
        for file_path in file_list:
            actual_path = os.path.join(base_path, file_path) if base_path else file_path
            should_exclude, reason = self.should_exclude_with_reason(file_path, actual_path)
            
            if should_exclude:
                excluded_files.append(file_path)
                exclusion_reasons[file_path] = reason
            else:
                allowed_files.append(file_path)
        
        return {
            'allowed': allowed_files,
            'excluded': excluded_files,
            'exclusion_reasons': exclusion_reasons,
            'total_files': len(file_list),
            'allowed_count': len(allowed_files),
            'excluded_count': len(excluded_files)
        }