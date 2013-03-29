#! /usr/bin/python
# -*- coding: utf-8 -*-



# import funkcí z jiného adresáře
import sys
import os.path

path_to_script = os.path.dirname(os.path.abspath(__file__))
#sys.path.append(os.path.join(path_to_script, "../extern/pycat/"))
sys.path.append(os.path.join(path_to_script, "../extern/pyseg_base/src"))
sys.path.append(os.path.join(path_to_script, "../extern/pycat/extern/py3DSeedEditor/"))
#sys.path.append(os.path.join(path_to_script, "../extern/"))
#import featurevector
import unittest

import logging
logger = logging.getLogger(__name__)


#import apdb
#  apdb.set_trace();
#import scipy.io
import numpy as np
import scipy

# ----------------- my scripts --------
import py3DSeedEditor
import dcmreaddata1 as dcmr
import pycat
import argparse
#import py3DSeedEditor

import segmentation
import qmisc


def interactive_imcrop(im):

    pass




class OrganSegmentation():
    def __init__(self, datadir, 
            working_voxelsize_mm = 0.25, 
            SeriesNumber = None, 
            autocrop = True, 
            autocrop_margin = [0,0,0], 
            manualroi = False, 
            texture_analysis=None, 
            smoothing_mm = 5, 
            data3d = None, 
            metadata=None, 
            seeds=None,
            edit_data = True

            ):
        """
        datadir: path to directory with dicom files
        manualroi: manual set of ROI before data processing, there is a 
             problem with correct coordinates
        data3d, metadata: it can be used for data loading not from directory. 
            If both are setted, datadir is ignored
        """
        
        self.datadir = datadir
        if np.isscalar(working_voxelsize_mm):
            self.working_voxelsize_mm = [working_voxelsize_mm] * 3
        else:
            self.working_voxelsize_mm = working_voxelsize_mm


        # TODO uninteractive Serie selection
        if data3d is None or metadata is None:
            self.data3d, self.metadata = dcmr.dcm_read_from_dir(datadir)
        else:
            self.data3d = data3d
            self.metadata = metadata


        self.seeds = seeds
        self.voxelsize_mm = self.metadata['voxelsizemm']
        self.autocrop = autocrop
        self.autocrop_margin = autocrop_margin
        self.crinfo = [[0,-1],[0,-1],[0,-1]]
        self.texture_analysis = texture_analysis
        self.smoothing_mm = smoothing_mm
        self.edit_data = edit_data

# manualcrop
        if manualroi:
# @todo opravit souřadný systém v součinnosti s autocrop
            self.data3d, self.crinfo = qmisc.manualcrop(self.data3d)

        
        if np.isscalar(working_voxelsize_mm):
            working_voxelsize_mm = np.ones([3]) * working_voxelsize_mm


        self.zoom = self.voxelsize_mm/working_voxelsize_mm

        #import pdb; pdb.set_trace()


#    def 

    def _interactivity_begin(self):
        data3d_res = scipy.ndimage.zoom(self.data3d , self.zoom, mode= 'nearest', order = 1)
        data3d_res = data3d_res.astype(np.int16)
        igc = pycat.ImageGraphCut(data3d_res, gcparams = {'pairwiseAlpha':30}, voxelsize = self.working_voxelsize_mm)
# version comparison
        from pkg_resources import parse_version
        import sklearn
        if parse_version(sklearn.__version__) > parse_version('0.10'):
            #new versions
            cvtype_name=  'covariance_type'
        else:
            cvtype_name=  'cvtype'

        igc.modelparams = {'type':'gmmsame','params':{cvtype_name:'full', 'n_components':3}}
        if not self.seeds == None:
            #igc.seeds= self.seeds
            seeds_res = scipy.ndimage.zoom(self.seeds, self.zoom, mode= 'nearest', order = 0)
            seeds_res = seeds_res.astype(np.int8)
            igc.set_seeds(seeds_res)
            #print "nastavujeme seedy"
            #import py3DSeedEditor
            #rr=py3DSeedEditor.py3DSeedEditor(data3d_res, seeds = seeds_res); rr.show()

            #import pdb; pdb.set_trace()

        return igc

    def _interactivity_end(self,igc):
# @TODO někde v igc.interactivity() dochází k přehození nul za jedničy, 
# tady se to řeší hackem
        sgm = (igc.segmentation == 0).astype(np.int8)
        segm_orig_scale = scipy.ndimage.zoom(sgm , 1.0/self.zoom, mode= 'nearest', order = 0).astype(np.int8)
        #print  np.sum(self.segmentation)*np.prod(self.voxelsize_mm)

# @TODO odstranit hack pro oříznutí na stejnou velikost
# v podstatě je to vyřešeno
        shp =  [\
                np.min([segm_orig_scale.shape[0],self.data3d.shape[0]]),\
                np.min([segm_orig_scale.shape[1],self.data3d.shape[1]]),\
                np.min([segm_orig_scale.shape[2],self.data3d.shape[2]]),\
                ]
        #self.data3d = self.data3d[0:shp[0], 0:shp[1], 0:shp[2]]

        self.segmentation = np.zeros(self.data3d.shape, dtype=np.int8)
        self.segmentation[0:shp[0], 0:shp[1], 0:shp[2]] = segm_orig_scale[0:shp[0], 0:shp[1], 0:shp[2]]  


        if not self.autocrop == None:

            self.crinfo = self._crinfo_from_specific_data(self.segmentation, self.autocrop_margin)
            self.segmentation = self._crop(self.segmentation, self.crinfo)
            self.data3d = self._crop(self.data3d, self.crinfo)


        if not self.texture_analysis == None:
            import texture_analysis
            # doplnit nějaký kód, parametry atd
            #self.orig_scale_segmentation = texture_analysis.segmentation(self.data3d, self.orig_scale_segmentation, params = self.texture_analysis)
            self.segmentation = texture_analysis.segmentation(self.data3d, self.segmentation, params = self.texture_analysis)
#
            pass


    def interactivity(self):
        
        #import pdb; pdb.set_trace()
# Staré volání
        #igc = pycat.ImageGraphCut(self.data3d, zoom = self.zoom)
        #igc.gcparams['pairwiseAlpha'] = 30
        #seeds_res = scipy.ndimage.zoom(self.seeds , self.zoom, prefilter=False, mode= 'nearest', order = 1)
        #seeds = self.seeds.astype(np.int8)

        if self.edit_data:
            self.data3d = self.data_editor(self.data3d)
        igc = self._interactivity_begin()
        igc.interactivity()
        self._interactivity_end(igc)
        #igc.make_gc()
        #igc.show_segmentation()

    def ninteractivity(self):
        """
        Function for automatic (noninteractiv) mode.
        """
        
        #import pdb; pdb.set_trace()
# Staré volání
        #igc = pycat.ImageGraphCut(self.data3d, zoom = self.zoom)
        #igc.gcparams['pairwiseAlpha'] = 30
        #seeds_res = scipy.ndimage.zoom(self.seeds , self.zoom, prefilter=False, mode= 'nearest', order = 1)
        #seeds = self.seeds.astype(np.int8)
        igc = self._interactivity_begin()
        #igc.interactivity()
        igc.make_gc()
        self._interactivity_end(igc)
        #igc.show_segmentation()

    def prepare_output(self):
        pass
        

    def get_segmented_volume_size_mm3(self):
        """
        Compute segmented volume in mm3, based on subsampeled data 
        """
        #voxelvolume_mm3 = np.prod(self.working_voxelsize_mm)
        #volume_mm3_rough = np.sum(self.segmentation > 0) * voxelvolume_mm3

        voxelvolume_mm3 = np.prod(self.voxelsize_mm)
        volume_mm3 = np.sum(self.segmentation > 0) * voxelvolume_mm3
        #import pdb; pdb.set_trace()


        #print " fine = ", volume_mm3 
        #print voxelvolume_mm3 
        #print volume_mm3
        #import pdb; pdb.set_trace()
        return volume_mm3

    def make_segmentation(self):
        pass


    def ni_set_roi(self, roi_mm):
        pass


    def ni_set_seeds(self, coordinates_mm, label, radius):
        pass

    def _crop(self, data, crinfo):
        """
        Crop data with crinfo
        """
        data = data[crinfo[0][0]:crinfo[0][1], crinfo[1][0]:crinfo[1][1], crinfo[2][0]:crinfo[2][1]]
        return data


    def _crinfo_from_specific_data (self, data, margin):
# hledáme automatický ořez, nonzero dá indexy
        nzi = np.nonzero(data)

        x1 = np.min(nzi[0]) - margin[0]
        x2 = np.max(nzi[0]) + margin[0] + 1
        y1 = np.min(nzi[1]) - margin[0]
        y2 = np.max(nzi[1]) + margin[0] + 1
        z1 = np.min(nzi[2]) - margin[0]
        z2 = np.max(nzi[2]) + margin[0] + 1 

# ošetření mezí polí
        if x1 < 0:
            x1 = 0
        if y1 < 0:
            y1 = 0
        if z1 < 0:
            z1 = 0

        if x2 > data.shape[0]:
            x2 = data.shape[0]-1
        if y2 > data.shape[1]:
            y2 = data.shape[1]-1
        if z2 > data.shape[2]:
            z2 = data.shape[2]-1

# ořez
        crinfo = [[x1, x2],[y1,y2],[z1,z2]]
        #dataout = self._crop(data,crinfo)
        #dataout = data[x1:x2, y1:y2, z1:z2]
        return crinfo


    def im_crop(self, im,  roi_start, roi_stop):
        im_out = im[ \
                roi_start[0]:roi_stop[0],\
                roi_start[1]:roi_stop[1],\
                roi_start[2]:roi_stop[2],\
                ]
        return  im_out
    
    def segmentation_smoothing(self, sigma_mm):
        """
        shape of output segmentation is smoothed with gaussian filter. Sigma 
        is computed in mm
        """
        #print "smoothing"
        sigma = float(sigma_mm)/np.array(self.voxelsize_mm)

        #print sigma
        #import pdb; pdb.set_trace()
        self.orig_scale_segmentation = scipy.ndimage.filters.gaussian_filter(\
                self.orig_scale_segmentation.astype(float), sigma)
        #import pdb; pdb.set_trace()
        #pyed = py3DSeedEditor.py3DSeedEditor(self.orig_scale_segmentation)
        #pyed.show()

        self.orig_scale_segmentation = 1.0 * (self.orig_scale_segmentation> 0.5)

    def export(self):
        slab={}
        slab['none'] = 0
        slab['liver'] = 1
        slab['lesions'] = 6

        data = {}
        data['data3d'] = self.data3d
        data['crinfo'] = self.crinfo
        data['segmentation'] = self.segmentation
        data['slab'] = slab
        #import pdb; pdb.set_trace()
        return data


    def data_editor(self, im3d, cval = 0):
        """
        Funkce provádí změnu vstupních dat - data3d
        cval: hodnota, na kterou se nastaví "vymazaná" data
        """


        from seed_editor_qt import QTSeedEditor
        from PyQt4.QtGui import QApplication
        import numpy as np
#, QMainWindow
        print ("Select voxels for deletion")
        app = QApplication(sys.argv)
        pyed = QTSeedEditor(im3d, mode='draw')
        pyed.exec_()


        deletemask = pyed.getSeeds()
        #import pdb; pdb.set_trace()

        
        #pyed = QTSeedEditor(deletemask, mode='draw')
        #pyed.exec_()

        app.exit()
        #pyed.exit()
        del app
        del pyed

        im3d[deletemask != 0] = cval
        #print ("Check output")
        # rewrite input data
        #pyed = QTSeedEditor(im3d)
        #pyed.exec_()

        #el pyed
        
        #import pdb; pdb.set_trace()

        return im3d

        




class Tests(unittest.TestCase):
    def setUp(self):
        """ Nastavení společných proměnných pro testy  """
        self.assertTrue(True)
    def test_whole_organ_segmentation(self):
        """
        Function uses organ_segmentation object for segmentation
        """
        dcmdir = './../sample_data/matlab/examples/sample_data/DICOM/digest_article/'
        oseg = OrganSegmentation(dcmdir, working_voxelsize_mm = 4)

        oseg.interactivity()

        roi_mm = [[3,3,3],[150,150,50]]
        oseg.ni_set_roi()
        coordinates_mm = [[110,50,30], [10,10,10]]
        label = [1,2]
        radius = [5,5]
        oseg.ni_set_seeds(coordinates_mm, label, radius)

        oseg.make_segmentation()

        #oseg.noninteractivity()
        pass

    def test_dicomread_and_graphcut(self):
        """
        Test dicomread module and graphcut module
        """
        #dcm_read_from_dir('/home/mjirik/data/medical/data_orig/46328096/')
        data3d, metadata = dcmr.dcm_read_from_dir('./../sample_data/matlab/examples/sample_data/DICOM/digest_article/')

        print ("Data size: " + str(data3d.nbytes) + ', shape: ' + str(data3d.shape) )

        igc = pycat.ImageGraphCut(data3d, zoom = 0.5)
        seeds = igc.seeds
        seeds[0,:,0] = 1
        seeds[60:66,60:66,5:6] = 2
        igc.noninteractivity(seeds)


        igc.make_gc()
        segmentation = igc.segmentation
        self.assertTrue(segmentation[14, 4, 1] == 0)
        self.assertTrue(segmentation[127, 120, 10] == 1)
        self.assertTrue(np.sum(segmentation==1) > 100)
        self.assertTrue(np.sum(segmentation==0) > 100)
        #igc.show_segmentation()


def main():

    #logger = logging.getLogger(__name__)
    logger = logging.getLogger()

    logger.setLevel(logging.WARNING)
    ch = logging.StreamHandler()
    logger.addHandler(ch)

    #logger.debug('input params')

    # input parser
    parser = argparse.ArgumentParser(description=
            'Segment vessels from liver \n \npython organ_segmentation.py\n \n python organ_segmentation.py -mroi -vs 0.6')
    parser.add_argument('-dd','--dcmdir',
            default=None,
            help='path to data dir')
    parser.add_argument('-d', '--debug', action='store_true',
            help='run in debug mode')
    parser.add_argument('-vs', '--voxelsizemm',default = '3', type = str,
            help='Insert working voxelsize. It can be number or \
            array of three numbers ')
    parser.add_argument('-mroi', '--manualroi', action='store_true',
            help='manual crop before data processing')
    parser.add_argument('-t', '--tests', action='store_true', 
            help='run unittest')
    parser.add_argument('-tx', '--textureanalysis', action='store_true', 
            help='run with texture analysis')
    parser.add_argument('-exd', '--exampledata', action='store_true', 
            help='run unittest')
    parser.add_argument('-ed', '--editdata', action='store_true', 
            help='Run data editor')
    args = parser.parse_args()

    # voxelsizemm can be number or array
    args.voxelsizemm = np.array(eval(args.voxelsizemm))


    if args.debug:
        logger.setLevel(logging.DEBUG)

    if args.tests:
        # hack for use argparse and unittest in one module
        sys.argv[1:]=[]
        unittest.main()
        sys.exit() 

    if args.exampledata:

        args.dcmdir = '../sample_data/matlab/examples/sample_data/DICOM/digest_article/'
        
    #else:
    #dcm_read_from_dir('/home/mjirik/data/medical/data_orig/46328096/')
        #data3d, metadata = dcmreaddata.dcm_read_from_dir()


    oseg = OrganSegmentation(args.dcmdir, 
            working_voxelsize_mm = args.voxelsizemm, 
            manualroi = args.manualroi, 
            texture_analysis = args.textureanalysis,
            edit_data = args.editdata
            )

    oseg.interactivity()


    #print ("Data size: " + str(data3d.nbytes) + ', shape: ' + str(data3d.shape) )

    #igc = pycat.ImageGraphCut(data3d, zoom = 0.5)
    #igc.interactivity()


    #igc.make_gc()
    #igc.show_segmentation()

    # volume 
    #volume_mm3 = np.sum(oseg.segmentation > 0) * np.prod(oseg.voxelsize_mm)

    print ( "Volume " + str(oseg.get_segmented_volume_size_mm3()/1000000.0) + ' [l]' )
    
    #pyed = py3DSeedEditor.py3DSeedEditor(oseg.data3d, contour = oseg.segmentation)
    #pyed.show()

    savestring = raw_input ('Save output data? (y/n): ')
    #sn = int(snstring)
    if savestring in ['Y','y']:
        import misc

        data = oseg.export()

        misc.obj_to_file(data, "organ.pickle", filetype = 'pickle')
    #output = segmentation.vesselSegmentation(oseg.data3d, oseg.orig_segmentation)
    

if __name__ == "__main__":
    main()
