import matplotlib.pyplot as plt
import numpy as np
from sklearn import datasets, linear_model
from sklearn.cross_validation import ShuffleSplit
from sklearn.metrics import r2_score
from collections import defaultdict
from sklearn.ensemble import RandomForestRegressor
from sklearn import mixture
import ipdb

from chumpy.ch import MatVecMult, Ch

class segmentCRFModel(Ch):
    dterms = ['renderer', 'groundtruth', 'priorProbs']

    def compute_r(self):
        return self.segmentation()

    def compute_dr_wrt(self, wrt):
        return None
    #     if wrt is self.renderer:
    #         return self.segmentation().dr_wrt(self.renderer)

    def segmentation(self):
        import densecrf_model

        vis_im = np.array(self.renderer.indices_image == 1).copy().astype(np.bool)
        bound_im = self.renderer.boundarybool_image.astype(np.bool)

        #
        segmentation, Q = densecrf_model.crfInference(self.groundtruth.r, vis_im, bound_im, [self.priorProbs[0], self.priorProbs[1], self.priorProbs[2]],
                                                      self.resultDir + 'imgs/crf/Q_' + str(self.test_i))
        return Q




def evaluatePrediction(azsGT, elevsGT, azsPred, elevsPred):
    errazs = np.arctan2(np.sin(azsGT - azsPred), np.cos(azsGT - azsPred))*180/np.pi
    errelevs = np.arctan2(np.sin(elevsGT-elevsPred), np.cos(elevsGT-elevsPred))*180/np.pi
    return errazs, errelevs

def trainRandomForest(xtrain, ytrain):
    randForest = RandomForestRegressor(n_estimators=400, n_jobs=-1)
    rf = randForest.fit(xtrain, ytrain)
    return rf

def testRandomForest(randForest, xtest):
    return randForest.predict(xtest)

def filteredMean(image, win):
    pixels = image[image.shape[0]/2-win:image.shape[0]/2+win,image.shape[1]/2-win:image.shape[1]/2+win,:]
    pixels = pixels.reshape([-1,3])
    gray = 0.3*pixels[:,0] + 0.59*pixels[:,1] + 0.11*pixels[:,2]
    stdM = 2
    pixels[np.abs(gray - np.mean(gray)) < stdM * np.std(gray),:]
    color = np.mean(image)
    return color

def meanColor(image, win):
    image = np.mean(image[image.shape[0]/2-win:image.shape[0]/2+win,image.shape[1]/2-win:image.shape[1]/2+win,:], axis=0)
    color = np.mean(image, axis=0)
    return color

def medianColor(image, win):
    imageWin = image[image.shape[0]/2-win:image.shape[0]/2+win,image.shape[1]/2-win:image.shape[1]/2+win,:]
    color = np.median(imageWin.reshape([-1,3]), axis=0)
    return color

def midColor(image):
    color = image[image.shape[0]/2,image.shape[1]/2,:]
    return color

def colorGMM(image, win):
    np.random.seed(1)
    gmm = mixture.GMM(n_components=8, covariance_type='spherical')
    colors = image[image.shape[0]/2-win:image.shape[0]/2+win,image.shape[1]/2-win:image.shape[1]/2+win,:][:,3]
    gmm.fit(colors)
    gmm._weights=np.array([0.6,0.3,0.1,0,0,0,0,0])
    return gmm

from scipy.stats import vonmises

def poseGMM(azimuth, elevation):
    np.random.seed(1)
    components = [0.7,0.05,0.05,0.05,0.05,0.05,0.05]
    azs = np.random.uniform(0,2*np.pi, 6)
    elevs = np.random.uniform(0,np.pi/2, 6)
    kappa = 50
    vmParamsAz = [(azs[i],kappa) for i in azs]
    vmParamsEl = [(elevs[i], kappa) for i in elevs]
    vmParamsAz = [(azimuth, kappa)]  + vmParamsAz
    vmParamsEl = [(elevation, kappa)]  + vmParamsEl
    return components, vmParamsAz, vmParamsEl


def trainLinearRegression(xtrain, ytrain):
    # Create linear regression object
    regr = linear_model.LinearRegression(n_jobs=-1)
    # Train the model using the training sets
    regr.fit(xtrain, ytrain)
    # print('Coefficients: \n', regr.coef_)
    #
    #       % (regr.predict(diabetes_X_test) - diabetes_y_test) ** 2))
    # Explained variance score: 1 is perfect prediction
    # print('Variance score: %.2f' % regr.score(diabetes_X_test, diabetes_y_test))

    # Plot outputs
    # plt.scatter(xtest, ytest,  color='black')
    return regr


def testLinearRegression(lrmodel, xtest):

    return lrmodel.predict(xtest)

class sphericalHarmonicsModel():

    def __init__(self, image=None, barycentric=None, visibility=None, SHComponents=None, f=None, vc=None, vn=None):

        self.SHComponents = SHComponents
        self.vn = vn
        self.visibility = visibility
        self.f = f
        self.vc = vc
        self.vn = vn
        self.barycentric = None
        visible = np.nonzero(visibility.ravel() != 4294967295)[0]
        vertexpix = np.where(self.barycentric[visible].ravel() <= 0.01)
        fvis = f[visibility.ravel()[visible]].ravel()[vertexpix]
        vcvis = vc[fvis]
        vnvis = vn[fvis]

        imvis = image[visible]

        evis = imvis/(vcvis+1e-5)

        self.X = vnvis
        self.y = evis

    # def fit(self, X, y):
    #
    #
    #
    # def score(self, X, y):
    #
    # def predict(self, X):

def solveSHCoefficients(groundtruth, visibility, f, vn, vc):

    #RANSAC solution.


    #1 Select nine vertices.

    #2 Get E by dividing by vc.

    #3 We know the normalizing constant and transfer function. What is A_l? Probably wrt vertex normals.

    #4 Solve the coefficients.
    bestVertices = None
    return bestVertices

