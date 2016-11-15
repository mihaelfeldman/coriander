define float *@someFunc(float * %d1, float *%v1) {
    %1 = fadd float 3.0, 4.0
    %2 = load float, float *%d1
    %3 = getelementptr float , float *%d1, i32 3
    store float %2, float *%3
    ret float *%3
}

define void @someKernel(float * %d1, float * %d2) {
    %1 = alloca float *, i32 1
    %2 = load float *, float **%1
    %3 = call float * @someFunc(float *%d1, float *%2)
    %4 = call float * @someFunc(float *%2, float *%d1)
    %5 = call float * @someFunc(float *%d1, float *%d1)
    ret void
}

;  %29 = getelementptr %struct.mystruct , %struct.mystruct *%24, i32 0, i32 0

define void @kernelBranches(float *%d1) {
label1:
    %0 = fadd float 3.0, 4.0
    br label %label2

label2:
    %1 = fadd float 5.0, 7.0
    %2 = fcmp ogt float %1, 6.0
    br i1 %2, label %label1, label %label2
}