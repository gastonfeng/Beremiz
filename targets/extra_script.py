import hashlib

Import("env", "projenv")
for e in [env, projenv]:
    e.Replace(LINKFLAGS=[i for i in e['LINKFLAGS'] if i not in ['-nostartfiles', '-nostdlib']])
    e.Append(LINKFLAGS=["--specs=nosys.specs"])

# access to global construction environment
# print env

# access to project construction environment
# print projenv

# Dump construction environments (for debug purpose)
# print env.Dump()
# print projenv.Dump()

# def before_buildprog(source, target, env):
#     print("before_buildprog")
#     print(os.getcwd())
# if os.path.exists('web'):
#     os.system("makefsdata.exe web")

# env.Append(ldscript='stm32f103ve.ld')


def before_upload(source, target, env):
    print("before_upload")
    # do some actions


def after_upload(source, target, env):
    print("after_upload")
    # do some actions


def buildMD5(source, target, env):
    print("buildMD5")
    f = str(target[0])
    print(f, type(f))
    fh = open(f, "rb")
    fr = fh.read()
    md5key = hashlib.md5(fr).hexdigest()

    # Store new PLC filename based on md5 key
    f = open("lastbuildPLC.md5", "w")
    f.write(md5key)
    f.close()


env.AddPreAction("upload", before_upload)
env.AddPostAction("upload", after_upload)
# env.AddPreAction("buildprog", before_buildprog)
# env.AddPostAction("$BUILD_DIR/firmware.bin", buildMD5)
# env.AddPostAction("$BUILD_DIR/program.dll", buildMD5)
