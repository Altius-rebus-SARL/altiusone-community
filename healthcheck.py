#!/usr/bin/env python
"""
Health check script for AltiusOne Docker container.
Used by Docker HEALTHCHECK to verify the application is running correctly.
"""
import os
import sys
import urllib.request
import urllib.error


def check_health():
    """Check if the Django application is responding."""
    host = os.environ.get('DJANGO_HOST', 'localhost')
    port = os.environ.get('DJANGO_PORT', '8000')
    health_url = f'http://{host}:{port}/health/'

    try:
        request = urllib.request.Request(health_url, method='GET')
        with urllib.request.urlopen(request, timeout=10) as response:
            if response.status == 200:
                print(f"Health check passed: {health_url}")
                return 0
            else:
                print(f"Health check failed: HTTP {response.status}")
                return 1
    except urllib.error.URLError as e:
        print(f"Health check failed: {e.reason}")
        return 1
    except Exception as e:
        print(f"Health check failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(check_health())
