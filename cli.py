import json
import yaml
import pprint
import re
import os
import touch
from jinja2 import Template
import jinja2

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

# declaring only, not change here
DEBUG=None
TEMPLATEDIR='templates'

def load(filename):
    try:
        with open(filename) as f:
            s = f.read()
    except IOError as x:
        if x.errno == errno.ENOENT:
            print(filename, '- does not exist')
        elif x.errno == errno.EACCES:
            print(filename, '- cannot be read')
        else:
            print(filename, '- some other error')

    data = {}
    if filename.endswith(".json"):
        data = json.loads(s)

    if filename.endswith(".yaml"):
        data = yaml.load(s, Loader=Loader)

    return data

def get_restyresolver(folder, path, method):
    verb        = method
    path_new    = path

    path_tree = path.split("/")
    
    if "{" not in path_tree[-1]:
        if method == "get":
            verb = "search"
    
    if "{" in path:
        path_new = re.sub(r'\{.*?\}', r'.', path_new)

    path_new = re.sub(r'/', r'', path_new)
    path_new = re.sub(r'\.$', r'', path_new)

    return {
        'operationId'  : "{folder}.{path_new}.{verb}".format(folder=folder, path_new=path_new, verb=verb),
        'folder'       : folder,
        'file'         : path_new,
        'verb'         : verb,
    }


def get_method_data(restyresolver, path, method, methodspec):
    if 'operationId' in methodspec:
        method_data = {
            'method':           method,
            'path':             path,
            'folder':           None,
            'file':             None,
            'verb':             method,
            'operationId':      methodspec['operationId'],
            'error':            False,
        }

    if 'operationId' not in methodspec:
        if restyresolver == None:
            method_data = {
                'method':           method,
                'path':             path,
                'folder':           None,
                'file':             None,
                'verb':             method,
                'operationId':      None,
                'error':            "WARNING: Method {path}/{method} don't have operationId defined and restyresolver is None".format(path=path, method=method),    
            }

        if restyresolver != None:
            resolver = get_restyresolver(restyresolver, path, method)
            
            method_data = {
                'method':           method,
                'path':             path,                            
                'folder':           resolver['folder'],
                'file':             resolver['file'],           
                'verb':             resolver['verb'],
                'operationId':      resolver['operationId'],
                'error':            False,     
            }
    return method_data

def get_method_parameters(methodparms):
    params = []
    for parm in methodparms:
        if 'name'in parm:
            params.append(parm['name'])

    return params      
            
def get_all_methods(specfile, restyresolver=None):
    methods = []
    spec = load(specfile)

    # each path
    if 'paths' not in spec:
        return methods

    for path in spec['paths']:
        # each method
        if path in spec['paths']:
            for method in spec['paths'][path]:
                if DEBUG == True:
                    print("\n\n############\nWorking on %(path)s/%(method)s ..." % {
                        'path':     path,
                        'method':   method,
                    })

                method_data = get_method_data(restyresolver, path, method, spec['paths'][path][method])

                method_parameters = []
                if 'parameters'in spec['paths'][path][method]:
                    method_parameters = get_method_parameters(spec['paths'][path][method]['parameters'])
                
                method_data['parameters'] = method_parameters

                if DEBUG == True:
                    pprint.pprint(method_data)

                methods.append(method_data)

    

    return methods

def get_tree(operationId):
    tree = operationId.split(".")
    return tree


def write_savefiles(savefiles):

    # small hack to write on __init__
    files = list(savefiles)
    files = sorted(files)

    # original : new
    filesmap = {}

    nfiles = []
    for f in files:
        if f.endswith(".py"):
            nfiles.append(re.sub(r'.py$', r'', f))
        if not f.endswith(".py"):
            nfiles.append(f)
    
    nfiles.append('generated/api/users')
    nfiles = sorted(list(set(nfiles)))
    nfiles = nfiles[1:]


    for nfile1 in nfiles:
        nfiledir = nfile1 + "/"
        for nfile2 in nfiles:
            #print(nfile2, nfile1)
            if nfile2.startswith(nfiledir):
                #print(nfiledir, nfile2) 
                nfile1full = nfile1 + ".py"
                filesmap[nfile1full] = nfiledir

    #pprint.pprint(filesmap)

    for fileout in savefiles:
        filewrite = fileout

        if fileout in filesmap:
            filewrite = filesmap[fileout] + "__init__.py"

        f = open(filewrite, "w")
        if len(savefiles[fileout]['import']) > 0:
            f.write("\n".join(savefiles[fileout]['import']))
            f.write("\n\n")
        
        if len(savefiles[fileout]['verb']) > 0:
            f.write("\n\n\n".join(savefiles[fileout]['verb']))
            f.write("\n\n\n")
        print("generating {filewrite}".format(filewrite=filewrite))  
        f.close()

def create_verb(verb, params):
    param_text = ", ".join(params)
    
    templateLoader = jinja2.FileSystemLoader(TEMPLATEDIR)
    templateEnv = jinja2.Environment(loader=templateLoader)
    TEMPLATE_FILE = "def.j2"
    template = templateEnv.get_template(TEMPLATE_FILE)
    verb_text = template.render(verb=verb, param_text=param_text)

    return verb_text

def add_savefiles(savefiles, filename, verbtype, content):
    if filename not in savefiles:
        savefiles[filename] = {'import' : [], 'verb' : []}
    
    if content not in savefiles[filename][verbtype]:
        savefiles[filename][verbtype].append(content)

def create_all_files(destdir, methods, apifile="api.py"):
    if os.path.isdir(destdir) == False:
        os.mkdir(destdir)

    destdir = re.sub(r'/$', r'', destdir)
    apifileout = "{destdir}/{apifile}".format(destdir=destdir, apifile=apifile)

    savefiles = {}

    for method in methods:
        # only create files when method has no error
        if method['error'] != False:
            print(method['error'])
            continue

        if DEBUG == True:
            pprint.pprint(method)

        tree = get_tree(method['operationId'])
        fileout = ''

        if len(tree) > 0:
            destdir_module = []
            destdir_n = 0

            if DEBUG == True:
                pprint.pprint(tree)

            tree_dirs = tree[:-1]


            if len(tree_dirs) > 0:
                tree_dirs_path = destdir
                tree_dirs_n = 0
                for d in tree_dirs:
                    tree_dirs_path = tree_dirs_path + "/" + d

                    if tree_dirs_n + 1 < len(tree_dirs):
                        if os.path.exists(tree_dirs_path) == False:
                            print("creating dir {tree_dirs_path}".format(tree_dirs_path=tree_dirs_path))
                            os.mkdir(tree_dirs_path)

                        if os.path.exists(tree_dirs_path + "/__init__.py") == False:
                            print("creating file {tree_dirs_path}/__init__.py".format(tree_dirs_path=tree_dirs_path))
                            touch.touch(tree_dirs_path + "/__init__.py")

                    tree_dirs_n += 1

            if len(tree) > 1:
                fileout = destdir + "/" + "/".join(tree_dirs) + ".py" 
            else:
                fileout = apifileout

            tree_verb = tree[-1]
            print("verb: ", tree_verb)
            verb_text = create_verb(verb=tree_verb, params=method['parameters'])
            add_savefiles(savefiles, fileout, "verb", verb_text)

            if len(tree_dirs) > 0:
                import_text = "import " + ".".join(tree_dirs)
                add_savefiles(savefiles, apifileout, "import", import_text)

    write_savefiles(savefiles)



def main(specfile, destdir, apifile="api.py", restyresolver=None, debug=False, templatedir='templates'):
    global DEBUG
    DEBUG=debug

    global TEMPLATEDIR 
    TEMPLATEDIR=templatedir

    methods = get_all_methods(specfile, restyresolver)
    create_all_files(destdir, methods)

    #pprint.pprint(j)



if __name__ == '__main__':
    # with Automatic Routing
    main('openapi_3.0_example.yaml', destdir='generated', restyresolver='api', debug=False, templatedir='templates')
    # without Automatic Routing
    #main('openapi_3.0_example.json', destdir='generated', debug=False, templatedir='templates')


    