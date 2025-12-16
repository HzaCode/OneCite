#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
 OneCite 
"""

import sys
import os

#  Python 
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_basic_import():
    """"""
    from onecite import process_references
    assert process_references is not None

def test_readme_example():
    """ README """
    from onecite import process_references
    
    # README 
    input_content = """10.1038/nature14539

Attention is all you need
Vaswani et al.
NIPS 2017"""
    
    # 
    def auto_select_callback(candidates):
        # 
        return 0 if candidates else -1
    
    result = process_references(
        input_content=input_content,
        input_type="txt",
        template_name="journal_article_full",
        output_format="bibtex",
        interactive_callback=auto_select_callback
    )
    
    assert result is not None
    assert 'results' in result
    assert 'report' in result

def test_apa_format():
    """ APA """
    from onecite import process_references
    
    input_content = "10.1038/nature14539"
    
    def auto_select_callback(candidates):
        return 0 if candidates else -1
    
    result = process_references(
        input_content=input_content,
        input_type="txt",
        template_name="journal_article_full",
        output_format="apa",
        interactive_callback=auto_select_callback
    )
    
    assert result is not None
    assert 'results' in result

def main():
    """"""
    print("  OneCite \n")
    
    tests = [
        ("", test_basic_import),
        ("README ", test_readme_example),
        ("APA ", test_apa_format),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f" {test_name}")
        print('='*50)
        
        if test_func():
            passed += 1
        
    print(f"\n{'='*50}")
    print(f" : {passed}/{total} ")
    print('='*50)
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

