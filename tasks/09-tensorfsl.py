from core.generictask import GenericTask
from lib.images import Images
import os

__author__ = 'desmat'

class TensorFsl(GenericTask):


    def __init__(self, subject):
        """Fits a diffusion tensor model at each voxel
        """
        GenericTask.__init__(self, subject, 'upsampling', 'registration', 'qa')


    def implement(self):
        """Placeholder for the business logic implementation

        """

        dwi = self.getUpsamplingImage('dwi', 'upsample')
        bVals = self.getUpsamplingImage('grad', None, 'bvals')
        bVecs = self.getUpsamplingImage('grad', None, 'bvecs')
        #mask = self.getImage(self.maskingDir, 'anat', ['resample', 'extended', 'mask'])
        mask = self.getRegistrationImage('mask', 'resample')

        self.__produceTensors(dwi, bVecs, bVals, mask)

        l1 = self.getImage('dwi', 'l1')
        l2 = self.getImage('dwi', 'l2')
        l3 = self.getImage('dwi', 'l3')

        ad = self.buildName(dwi, 'ad')
        rd = self.buildName(dwi, 'rd')

        self.rename(l1, ad)
        self.__mean(l2, l3, rd)


    def __produceTensors(self, source, bVecs, bVals, mask=""):
        """Fits a diffusion tensor model at each voxel

        Args:
            source: A diffusion weighted volumes and volume(s) with no diffusion weighting
            bVecs: Text file containing a list of gradient directions applied during diffusion weighted volumes.
            bVals: Text file containing a list of b values applied during each volume acquisition.
            mask: A binarised volume in diffusion space containing ones inside the brain and zeroes outside the brain.

        """
        self.info("Starting dtifit from fsl")
        target = self.buildName(source, None,  '')
        cmd = "dtifit -k {} -o {} -r {} -b {} --save_tensor --sse ".format(source, target, bVecs, bVals)
        if mask:
            cmd += "-m {}".format(mask)
        self.launchCommand(cmd)

        fslPostfix = {'fa': 'FA', 'md': 'MD', 'mo': 'MO', 'so': 'S0',
                      'v1': 'V1', 'v2': 'V2', 'v3': 'V3', 'l1': 'L1', 'l2': 'L2', 'l3': 'L3'}
        for postfix, value in fslPostfix.iteritems():
            src = self.buildName(source, value)
            dst = self.buildName(source, postfix)
            self.info("rename {} to {}".format(src, dst))
            os.rename(src, dst)

    def __mean(self, source1, source2, target):
        cmd = "fslmaths {} -add {} -div 2 {}".format(source1, source2, target)
        self.launchCommand(cmd)


    def isIgnore(self):
        return self.get("ignore")


    def meetRequirement(self, result=True):
        """Validate if all requirements have been met prior to launch the task

        """
        return Images((self.getUpsamplingImage('dwi','upsample'), 'diffusion weighted'),
                  (self.getRegistrationImage('mask', 'resample'), 'brain mask'),
                  (self.getUpsamplingImage('grad', None, 'bvals'), '.bvals gradient encoding file'),
                  (self.getUpsamplingImage('grad', None, 'bvecs'), '.bvecs gradient encoding file'))


    def isDirty(self):
        """Validate if this tasks need to be submit for implementation

        """
        return Images((self.getImage('dwi', 'v1'), "1st eigenvector"),
                      (self.getImage('dwi', 'v2'), "2rd eigenvector"),
                      (self.getImage('dwi', 'v3'), "3rd eigenvector"),
                      (self.getImage('dwi', 'ad'), "selected eigenvalue(s) AD"),
                      (self.getImage('dwi', 'rd'), "selected eigenvalue(s) RD"),
                      (self.getImage('dwi', 'md'), "mean diffusivity"),
                      (self.getImage('dwi', 'fa'), "fractional anisotropy"),
                      (self.getImage('dwi', 'so'), "raw T2 signal with no weighting"))


    def qaSupplier(self):
        """Create and supply images for the report generated by qa task

        """
        qaImages = Images()
        softwareName = 'fsl'

        #Get images
        mask = self.getRegistrationImage('mask', 'resample')

        #Build qa images
        tags = (
            ('fa', 'Fractional anisotropy'),
            ('ad', 'Axial Diffusivity'),
            ('md', 'Mean Diffusivity'),
            ('rd', 'Radial Diffusivity'),
            ('sse', 'Sum of squared errors'),
            )

        for postfix, description in tags:
            image = self.getImage('dwi', postfix)
            if image:
                qaImage = self.buildName(image, softwareName, 'png')
                self.slicerPng(image, qaImage, boundaries=mask)
                qaImages.extend(Images((qaImage, description)))

        return qaImages
