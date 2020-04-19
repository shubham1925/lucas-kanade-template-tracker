import cv2 as cv
import glob
import numpy as np
import copy

images = []
original_frame = []
for file in glob.glob("car/*.jpg"):
    frame = cv.imread(file)
    grey = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    images.append(grey)
    original_frame.append(frame)

#not being used currently
def adjust_brightness(image, gamma=1.0):
	invGamma = 1.0 / gamma
	table = np.array([((i / 255.0) ** invGamma) * 255
		for i in np.arange(0, 256)]).astype("uint8")
	return cv.LUT(image, table)

def affine_matrix(p):    
    W = np.array([[1, 0, 0], [0, 1, 0]]) + p.reshape((2,3), order = 'F')
    return W

def lucas_kanade_tracker(img, tmp, rect, p_prev, flag):
    iterations = 0
    gain = 10
    cost_function = 1
    threshold = 0.006 #check different threshold
    W = affine_matrix(p_prev)    
    
#    tmp_2 = copy.deepcopy(tmp)

    while cost_function > threshold:
        iterations = iterations + 1
        
        #form the warped image  - Step 1
        Iw = cv.warpAffine(img, W, (0, 0), flags=cv.INTER_CUBIC + cv.WARP_INVERSE_MAP)#combination trial 
        cv.imshow("warped", Iw)
        Iw = Iw[rect[0,1]:rect[2,1] , rect[0,0]:rect[2,0]]
#        cv.imshow("warped", Iw)
#        Iw_2 = copy.deepcopy(Iw)   
        
        #Todo
        #Check if brightness has decreased for a frame and then increase it
#        print("warped: "+str(np.linalg.norm(Iw)))
#        print("template: "+str(np.linalg.norm(tmp)))
        
        """if np.linalg.norm(Iw) < 10000.0:
            tmp = cv.equalizeHist(Iw)
            Iw = adjust_brightness(tmp, 3)
            print("adjusted")"""
            
#        if np.linalg.norm(Iw) < np.linalg.norm(tmp):
#            img = adjust_brightness(img, gamma = 1.5)
#        
#        if np.linalg.norm(Iw) > np.linalg.norm(tmp):
#            img = adjust_brightness(img, gamma = 0.8)
        #calculating error - step 2
        error = tmp.flatten().astype(np.int)-Iw.flatten().astype(np.int)
#        cv2.imshow("error", cv2.subtract(tmp_2, Iw_2))
   
        #calculate the gradient of main image along x and y - step 3
        if flag == 0:
            grad_x = cv.Sobel(np.float32(img), cv.CV_64F, 1, 0, ksize =1) #changing kernel size improved results at start
            grad_y = cv.Sobel(np.float32(img), cv.CV_64F, 0, 1, ksize =1)
        if flag == 1:
            grad_x = cv.Sobel(np.float32(img), cv.CV_64F, 1, 0, ksize =5) #changing kernel size improved results at start
            grad_y = cv.Sobel(np.float32(img), cv.CV_64F, 0, 1, ksize =5)
        
        #calculating the warp of the gradient
        grad_x = cv.warpAffine(grad_x, W, (0, 0), flags=cv.INTER_CUBIC + cv.WARP_INVERSE_MAP)
        grad_y = cv.warpAffine(grad_y, W, (0, 0), flags=cv.INTER_CUBIC + cv.WARP_INVERSE_MAP)
        
        #selecting only the template area
        grad_x = grad_x[rect[0,1]:rect[2,1] , rect[0,0]:rect[2,0]]
        grad_y = grad_y[rect[0,1]:rect[2,1] , rect[0,0]:rect[2,0]]        
        
        #calculating jacobian and steepest descent image - step 4 and 5
        grid_x = np.asarray(list(range(grad_x.shape[1])))
        grid_y = np.asarray(list(range(grad_y.shape[0])))        
        grid_x , grid_y = np.meshgrid(grid_x, grid_y)         
        steepest_image = np.array([np.multiply(grad_x.flatten(),grid_x.flatten()),np.multiply(grad_y.flatten(),grid_x.flatten()),np.multiply(grad_x.flatten(),grid_y.flatten()),
             np.multiply(grad_y.flatten(),grid_y.flatten()),grad_x.flatten(),grad_y.flatten()]).T
    
        #hessian matrix - step 6
        H = np.dot(steepest_image.T,steepest_image)
        cv.imshow("steepest", steepest_image)
        
        #update parameters - step 7
        p_change = np.dot(np.linalg.pinv(H), np.dot(steepest_image.T, error)) 
        
        #compositional image alignment trial -> not much change in the results
        p0,p1,p2,p3,p4,p5 = p_change[0], p_change[1], p_change[2], p_change[3], p_change[4], p_change[5]
        
#        p_prev[0] = p_prev[0] + p0 + p_prev[0]*p0 + p_prev[2]*p1
#        p_prev[1] = p_prev[1] + p1 + p_prev[1]*p0 + p_prev[3]*p1
#        p_prev[2] = p_prev[2] + p2 + p_prev[0]*p2 + p_prev[2]*p3
#        p_prev[3] = p_prev[3] + p3 + p_prev[1]*p2 + p_prev[3]*p3
#        p_prev[4] = p_prev[4] + p4 + p_prev[0]*p4 + p_prev[2]*p5
#        p_prev[5] = p_prev[5] + p5 + p_prev[1]*p4 + p_prev[3]*p5
        
        #calculate updated cost function
        cost_function = np.linalg.norm(p_change)
        #Normal LKT parameter update formula
        if flag == 0:
            p_prev = p_prev + p_change
        if flag == 1:
            p_prev = p_prev + p_change*gain
        W = affine_matrix(p_prev)

        if(iterations > 1000):
            break
#    print("iterations : " + str(iterations))
    return p_prev

vid_output = cv.VideoWriter('lkt_car.avi', cv.VideoWriter_fourcc('M', 'J', 'P', 'G'), 10, (images[0].shape[1], images[0].shape[0]))


rect1 = np.array([[70,51], [177,51], [177,138], [70,138]])
#rect2 = np.array([[132,63], [205,63], [205,119], [132,119]])
rect2 = np.array([[136,61], [209,61], [209,110], [136,110]])
#rect3 = np.array([[202,69], [257,69], [257,114], [202,114]]) #300
rect3 = np.array([[203,69], [267,69], [267,116], [203,116]])
#rect3 = np.array([[182,65], [248,65], [248,115], [182,115]])
rect4 = np.array([[203,69], [267,69], [267,116], [203,116]])

rect214 = np.array([[146,68], [213,68], [213,123], [146,123]])

param_1 = np.zeros(6) 
param_2 = np.zeros(6)
param_3 = np.zeros(6)
param_4 = np.zeros(6)

template1 = images[0][rect1[0,1]:rect1[2,1] , rect1[0,0]:rect1[2,0]]
template2 = images[200][rect2[0,1]:rect2[2,1] , rect2[0,0]:rect2[2,0]]
#template3 = images[315][rect3[0,1]:rect3[2,1] , rect3[0,0]:rect3[2,0]]
#template3 = images[264][rect3[0,1]:rect3[2,1] , rect3[0,0]:rect3[2,0]]
template3 = images[214][rect214[0,1]:rect214[2,1] , rect214[0,0]:rect214[2,0]]
template4 = images[315][rect4[0,1]:rect4[2,1] , rect4[0,0]:rect4[2,0]]

rect_updated_1 = copy.deepcopy(rect1)
rect_updated_2 = copy.deepcopy(rect2)
rect_updated_3 = copy.deepcopy(rect214)
rect_updated_4 = copy.deepcopy(rect4)

for i in range(1,len(images)):
    print("Frame no : "+str(i))    
    if i < 214:
        param_1 = lucas_kanade_tracker(images[i], template1, rect1, param_1, flag = 0)        
        w1 = affine_matrix(param_1)
        #draw rectange as per updated parameters
        rectTemp1 = np.dot(w1,np.vstack((rect1.T, np.ones((1,4))))).T
        #extract corner elements
        [xmax1, ymax1] = list(np.max(rectTemp1, axis = 0).astype(np.int))
        [xmin1, ymin1] = list(np.min(rectTemp1, axis = 0).astype(np.int))
        #create new rectangle/bounding box
        rect_updated_1=np.array([[xmin1,ymin1],[xmax1,ymin1],[xmax1,ymax1],[xmin1,ymax1]])        
        output = cv.polylines(original_frame[i],[rect_updated_1],True,(0,0,255),thickness = 2)
        vid_output.write(output)
        cv.imshow("tracker",output)
    elif i >= 200 and i < 214:
        param_2 = lucas_kanade_tracker(images[i], template2, rect2, param_2, flag = 0)
        w2 = affine_matrix(param_2)
        rectTemp2 = np.dot(w2,np.vstack((rect2.T, np.ones((1,4))))).T
        [xmax2, ymax2] = list(np.max(rectTemp2, axis = 0).astype(np.int))
        [xmin2, ymin2] = list(np.min(rectTemp2, axis = 0).astype(np.int))
        rect_updated_2=np.array([[xmin2,ymin2],[xmax2,ymin2],[xmax2,ymax2],[xmin2,ymax2]])        
        output = cv.polylines(original_frame[i],[rect_updated_2],True,(0,0,255),thickness = 2)
        cv.imshow("tracker",output)
    elif i >= 214 and i < 315:
        param_3 = lucas_kanade_tracker(images[i], template3, rect214, param_3, flag = 0)
        w3 = affine_matrix(param_3)
        rectTemp3 = np.dot(w3,np.vstack((rect214.T, np.ones((1,4))))).T
        [xmax3, ymax3] = list(np.max(rectTemp3, axis = 0).astype(np.int))
        [xmin3, ymin3] = list(np.min(rectTemp3, axis = 0).astype(np.int))
        rect_updated_214 = np.array([[xmin3,ymin3],[xmax3,ymin3],[xmax3,ymax3],[xmin3,ymax3]])        
        output = cv.polylines(original_frame[i],[rect_updated_214],True,(0,0,255),thickness = 2)
        vid_output.write(output)
        cv.imshow("tracker",output)
    elif i >= 315:
        param_4 = lucas_kanade_tracker(images[i], template4, rect4, param_4, flag = 1)
        w4 = affine_matrix(param_4)
        rectTemp4 = np.dot(w4,np.vstack((rect4.T, np.ones((1,4))))).T
        [xmax4, ymax4] = list(np.max(rectTemp4, axis = 0).astype(np.int))
        [xmin4, ymin4] = list(np.min(rectTemp4, axis = 0).astype(np.int))
        rect_updated_4 = np.array([[xmin4,ymin4],[xmax4,ymin4],[xmax4,ymax4],[xmin4,ymax4]])        
        output = cv.polylines(original_frame[i],[rect_updated_4],True,(0,0,255),thickness = 2)
        vid_output.write(output)
        cv.imshow("tracker",output)
        
    
    
    k = cv.waitKey(20) & 0xFF
    if k == 27:
        break 
vid_output.release()
cv.destroyAllWindows()