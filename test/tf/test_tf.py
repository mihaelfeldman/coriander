"""
Try to run a tf kernel
Check does/doesnt work
"""
import numpy as np
import pyopencl as cl
import subprocess
import math
from test import test_common
from test.test_common import compile_code


def test_cwise_sqrt(context, q, float_data, float_data_gpu):
    options = test_common.cocl_options()
    i = 0
    opt_options = []
    iropencl_options = []
    while i < len(options):
        if options[i] == '--devicell-opt':
            opt_options.append('-' + options[i + 1])
            i += 2
            continue
        if options[i] in ['--run_branching_transforms', '--branches_as_switch']:
            iropencl_options.append(options[i])
            i += 1
            continue
        raise Exception('unknown option ', options[i])
        i += 1
    print('opt_options', opt_options)
    print('iropencl_options', iropencl_options)
    res = subprocess.run([
        'opt-3.8'
    ] + opt_options + [
        '-S',
        'test/tf/samples/cwise_op_gpu_sqrt-device-noopt.ll',
        '-o', '/tmp/test-opt.ll'
    ], stdout=subprocess.PIPE)
    print(' '.join(res.args))
    assert res.returncode == 0

    res = subprocess.run([
        'build/ir-to-opencl'
    ] + iropencl_options + [
        '--inputfile', '/tmp/test-opt.ll',
        '--outputfile', '/tmp/test-device.cl'
    ], stdout=subprocess.PIPE)
    print(' '.join(res.args))
    assert res.returncode == 0

    with open('/tmp/test-device.cl', 'r') as f:
        cl_sourcecode = f.read()

    prog = cl.Program(context, cl_sourcecode).build()

    N = 10

    # global struct Eigen__TensorEvaluator_nopointers* eval_nopointers, global float* eval_ptr0, long eval_ptr0_offset, global float* eval_ptr1, long eval_ptr1_offset, int size, local int *scratch

    # what we need:
    # struct Eigen__TensorEvaluator_nopointers   Note that none of the values we copy across are actually use, so we can just create a sufficiently large buffer...
    # global float *eval_ptr0  => this will receive the result.  just create a sufficiently large buffer
    # ptr0_offset => 0
    # eval_ptr1 => will contian the data we want to reduce
    # eval_ptr1_offset=> 0
    # size =>  eg 10, to reduce 10 values
    # scratch => set to workgroupsize * sizeof(float)

    eval_nopointers_gpu = cl.Buffer(context, cl.mem_flags.READ_WRITE, size=4096)

    eval_ptr0 = np.zeros(1024, dtype=np.float32)
    eval_ptr0_gpu = cl.Buffer(context, cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR, hostbuf=eval_ptr0)
    eval_ptr0_offset = 0

    eval_ptr1 = np.random.uniform(0, 1, size=(1024,)).astype(np.float32) + 1.0
    eval_ptr1_gpu = cl.Buffer(context, cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR, hostbuf=eval_ptr1)
    eval_ptr1_offset = 0

    size = N

    global_size = 256
    workgroup_size = 256
    scratch = workgroup_size * 4

    prog.__getattr__('_ZN5Eigen8internal15EigenMetaKernelINS_15TensorEvaluatorIKNS_14TensorAssignOpINS_9TensorMapINS_6TensorIfLi1ELi1EiEELi16ENS_11MakePointerEEEKNS_18TensorCwiseUnaryOpINS0_14scalar_sqrt_opIfEEKNS4_INS5_IKfLi1ELi1EiEELi16ES7_EEEEEENS_9GpuDeviceEEEiEEvT_T0_')(
        q, (global_size,), (workgroup_size,),
        eval_nopointers_gpu,
        eval_ptr0_gpu, np.int64(eval_ptr0_offset),
        eval_ptr1_gpu, np.int64(eval_ptr1_offset),
        np.int32(size),
        cl.LocalMemory(scratch)
    )
    # check for errors
    q.finish()
    # copy eval_ptr0 back, and check the results...
    cl.enqueue_copy(q, eval_ptr0, eval_ptr0_gpu)
    q.finish()
    print('eval_ptr0[:N]', eval_ptr0[:N])

    expected = np.sqrt(eval_ptr1)
    print('expected[:10]', expected[:N])
    assert np.abs(expected[:N] - eval_ptr0[:N]).max() < 1e-4
