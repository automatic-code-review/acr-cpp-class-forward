import os
import re
import subprocess
import json
import automatic_code_review_commons as commons

def review(config):
    path_source = config['path_source']
    changes = config['merge']['changes']
    comments = []
    ignore = config['regex_to_ignore']
    comment_description = config['message']

    for change in changes:
        if change['deleted_file']:
            continue

        new_path = change['new_path']
        full_path = path_source + "/" + new_path

        if not full_path.endswith('.h'):
            continue

        comments.extend(__review_by_file(full_path, path_source, ignore, comment_description))

    return comments

def __check_regex_list(regex_list, text):
    for regex in regex_list:
        if re.match(regex, text):
            return True

    return False

def __load_inheritance(path):
    inheritance = []

    data = subprocess.run(
        'ctags --output-format=json --format=2 --fields=+line ' + path,
        shell=True,
        capture_output=True,
        text=True,
    ).stdout

    for obj in data.split('\n'):
        if obj == '':
            continue

        obj = json.loads(obj)

        if 'inherits' in obj:
            inheritance.append(obj['inherits'])

    return inheritance

def __review_by_file( path, path_source, ignore, comment_description):
    with open(path, 'r') as arquivo:
        lines = arquivo.readlines()

    regex_list_to_ignore = [".*ui_.*", ".*\.moc"] + ignore

    inheritance = __load_inheritance( path )

    for inherit in inheritance:
        regex_list_to_ignore.append(f'.*{inherit.lower()}.h')

    comments = []
    line_number = 0
    lines_already_processed = []

    for line in lines:
        line_number += 1
        line = line.strip()

        if not line.startswith("#include "):
            continue

        if __check_regex_list(regex_list_to_ignore, line):
            continue

        if line in lines_already_processed:
            continue

        lines_already_processed.append(line)

        comments.extend(__review_by_line(
            line=line,
            path=path,
            path_source=path_source,
            line_number=line_number,
            comment_description=comment_description
        ))

    return comments

def __review_by_line(line, path, path_source, line_number, comment_description):
    comments = []
    include_path = line[9:].strip().strip('"').strip('<').strip('>')

    if __is_same_layer(include_path, path, path_source):
        comment_path = path.replace(path_source, '')[1:]
        comment_description = comment_description.replace('${INCLUDE_PATH}', include_path)
        comment_description = comment_description.replace('${FILE_PATH}', comment_path)
        
        comments.append(commons.comment_create(
            comment_id=commons.comment_generate_id(comment_description),
            comment_path=comment_path,
            comment_description=comment_description,
            comment_snipset=True,
            comment_end_line=line_number,
            comment_start_line=line_number,
            comment_language='c++',
        ))
    
    return comments

def __is_same_layer(include_path, path, path_source):
    relative_path = os.path.relpath(path, path_source)
    
    return relative_path.split('/')[0] == include_path.split('/')[0]