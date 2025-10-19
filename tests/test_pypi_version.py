#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
 PyPI  onecite 0.0.6
"""

import subprocess
import sys

def test_pypi_version():
    """ PyPI """

    print("===  PyPI  onecite 0.0.6 ===")

    # 
    try:
        import onecite
        print(f" : {onecite.__version__}")
        print(f" : {onecite.__author__}")
    except ImportError as e:
        print(f" : {e}")
        return False

    # 
    print("\n---  ---")

    # 
    try:
        result = subprocess.run([sys.executable, "-m", "onecite.cli", "--help"],
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(" CLI ")
            print(":")
            print(result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout)
        else:
            print(f" CLI : {result.stderr}")
            return False
    except Exception as e:
        print(f" CLI : {e}")
        return False

    # 
    print("\n---  ---")

    test_input = """10.1038/nature14539
Attention is all you need
BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding"""

    try:
        with open("test_refs.txt", "w", encoding="utf-8") as f:
            f.write(test_input)

        # 
        result = subprocess.run([
            sys.executable, "-m", "onecite.cli",
            "process", "test_refs.txt",
            "--quiet"
        ], capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            print(" ")
            print(":")
            output_lines = result.stdout.strip().split('\n')
            for line in output_lines[:5]:  # 5
                print(f"  {line}")
            if len(output_lines) > 5:
                print(f"  ... ( {len(output_lines)} )")
        else:
            print(f" : {result.stderr}")
            return False

    except Exception as e:
        print(f" : {e}")
        return False
    finally:
        # 
        try:
            import os
            if os.path.exists("test_refs.txt"):
                os.remove("test_refs.txt")
        except:
            pass

    #  Python API
    print("\n---  Python API ---")

    try:
        from onecite import process_references

        def simple_callback(candidates):
            return 0 if candidates else -1

        result = process_references(
            input_content="10.1038/nature14539",
            input_type="txt",
            template_name="journal_article_full",
            output_format="bibtex",
            interactive_callback=simple_callback
        )

        if result and result.get('results'):
            print(" Python API ")
            print("API :")
            print(result['results'][0][:200] + "..." if len(result['results'][0]) > 200 else result['results'][0])
        else:
            print(" Python API ")
            return False

    except Exception as e:
        print(f" API : {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n PyPI  onecite 0.0.6 ")
    return True

if __name__ == "__main__":
    success = test_pypi_version()
    if not success:
        sys.exit(1)




