import cv2
import torch
import numpy as np
import open3d as o3d
import pyrealsense2 as rs
import matplotlib.pyplot as plt
#import tensorflow_hub as tf_hub
#from transformers import AutoProcessor
import torchvision.transforms as transforms
from transformers import BeitForSemanticSegmentation
from transformers import pipeline, AutoModel, AutoImageProcessor
from transformers import OneFormerProcessor, OneFormerForUniversalSegmentation
from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation

def get_rgb_and_depth_image():

    '''
        Functions is looking for RealSense camera and returns color and depth image.
        If camera is not found, function returns None, None
    '''

    try:
        pc = rs.pointcloud()
        points = rs.points()
        pipeline = rs.pipeline()
        config = rs.config()

        pipeline_wrapper = rs.pipeline_wrapper(pipeline)
        pipeline_profile = config.resolve(pipeline_wrapper)
        device = pipeline_profile.get_device()
        #device_product_line = str(device.get_info(rs.camera_info.product_line))

        found_rgb = False
        for s in device.sensors:
            if s.get_info(rs.camera_info.name) == 'RGB Camera':
                found_rgb = True
                print("Camera found")
                break
        if not found_rgb:
            print("No RGB camera found")
            return None, None
        
        config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        pipeline.start(config)
        colorizer = rs.colorizer()
        align_to = rs.stream.color
        align = rs.align(align_to)


        color_image = None
        depth_image = None
        print("Getting data...")

        while True:
            for _ in range(50):

                # Wait for a coherent pair of frames: depth and color
                frames = pipeline.wait_for_frames()
                aligned_frames = align.process(frames)
                colorized = colorizer.process(frames)
                
                depth_frame = aligned_frames.get_depth_frame()
                color_frame = aligned_frames.get_color_frame()
                if not depth_frame or not color_frame:
                    continue
                depth_image = np.asanyarray(frames.get_depth_frame().get_data())

                # Convert images to numpy arrays
                depth_image = np.asanyarray(depth_frame.get_data())
                color_image = np.asanyarray(color_frame.get_data())
                color_image = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)

                # Apply colormap on depth image (image must be converted to 8-bit per pixel first)
                depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image, alpha=0.033), cv2.COLORMAP_JET)

                depth_colormap_dim = depth_colormap.shape
                color_colormap_dim = color_image.shape

                # If depth and color resolutions are different, resize color image to match depth image for display
                if depth_colormap_dim != color_colormap_dim:
                    color_image = cv2.resize(color_image, dsize=(depth_colormap_dim[1], depth_colormap_dim[0]), interpolation=cv2.INTER_AREA)

            break

        ply = rs.save_to_ply('cloude_points.ply')
        pipeline.stop()
        return color_image, depth_image

    except Exception as e:
        print(e)
        return None, None
    

def get_point_cloud() -> o3d.geometry.PointCloud:
    '''
        Function is looking for RealSense camera and returns point cloud.
        If camera is not found, function returns None
    '''

    try:
        pc = rs.pointcloud()
        points = rs.points()
    
        pipeline = rs.pipeline()
        config = rs.config()
    
        pipeline_wrapper = rs.pipeline_wrapper(pipeline)
        pipeline_profile = config.resolve(pipeline_wrapper)
        device = pipeline_profile.get_device()
        #device_product_line = str(device.get_info(rs.camera_info.product_line))
    
        found_rgb = False
        for s in device.sensors:
            if s.get_info(rs.camera_info.name) == 'RGB Camera':
                found_rgb = True
                break
        if not found_rgb:
            print("No RGB camera found")
            return None
        
        config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
        config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        pipeline.start(config)
        colorizer = rs.colorizer()
        align_to = rs.stream.color
        align = rs.align(align_to)
    
        print("Getting data...")

        # depth_image = None
        color_image = None
        
        for _ in range(20):
            frames = pipeline.wait_for_frames()
            aligned_frames = align.process(frames)
            #colorized = colorizer.process(frames)

            depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()

        ply = rs.save_to_ply("./output.ply")
        print("done")
        pc.map_to(color_frame)
        points = pc.calculate(depth_frame)


        #vtx = np.asanyarray(points.get_vertices())
        #tex = np.asanyarray(points.get_texture_coordinates())

        #point_cloud = o3d.geometry.PointCloud()
        #point_cloud.points = o3d.utility.Vector3dVector(vtx.view(np.float32).reshape(-1, 3))
        #point_cloud.colors = o3d.utility.Vector3dVector(color_image.reshape(-1, 3) / 255.0)

        pipeline.stop()
        #return point_cloud
        return rs.pointcloud()
    
    except Exception as e:
        print(e)
        return None
    
    
def save_ply_file(filename: str):
    '''
        Function is looking for RealSense camera and saves point cloud to .ply file.
    '''
    pc = rs.pointcloud()
    points = rs.points()
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)

    colorizer = rs.colorizer()

    try:
        frames = pipeline.wait_for_frames()
        colorized = colorizer.process(frames)

        ply = rs.save_to_ply(f"{filename}.ply")
        ply.set_option(rs.save_to_ply.option_ply_binary, False)
        ply.set_option(rs.save_to_ply.option_ply_normals, True)

        print("Saving to {filename}.ply...")
        ply.process(colorized)
        print("Done")
    except Exception as e:
        print(e)

    finally:
        pipeline.stop()


def segment_knn(photo, centroids_number: int):
    '''
        Function takes a photo and returns segmented photo using knn algorythm.
    '''
    # Convert the image to RGB
    #photo = cv2.cvtColor(photo, cv2.COLOR_BGR2RGB)
    # Reshape the image to be a list of pixels
    pixels = photo.reshape(-1, 3)
    # Convert to float
    pixels = np.float32(pixels)
    # Define criteria, number of clusters and apply kmeans()
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    k = centroids_number
    _, labels, (centers) = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    # Convert back to 8 bit values
    centers = np.uint8(centers)
    segmented_data = centers[labels.flatten()]
    # Reshape back to the original image dimension
    segmented_image = segmented_data.reshape((photo.shape))
    return segmented_image, labels, centers

def segment_thresholding(photo, threshold: int):
    '''
        Function takes a photo and returns segmented photo using thresholding algorythm.
    '''
    gray = cv2.cvtColor(photo, cv2.COLOR_BGR2GRAY)
    _, segmented_image = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
    return segmented_image

def segment_local_thresholding(photo):
    '''
        Function takes a photo and returns segmented photo using local thresholding algorythm.
    '''
    gray = cv2.cvtColor(photo, cv2.COLOR_BGR2GRAY)
    segmented_image = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 2)
    return segmented_image

def segment_canny(photo, lower_boundry=100, upper_boundry=200):
    '''
        Function takes a photo and returns segmented photo using canny algorythm.
    '''
    gray = cv2.cvtColor(photo, cv2.COLOR_BGR2GRAY)
    segmented_image = cv2.Canny(gray, lower_boundry, upper_boundry)
    return segmented_image
    
def segment_sobel(photo, kernel_size=3, gray=True):
    '''
        Function takes a photo and returns segmented photo using sobel algorythm.
    '''
    if kernel_size % 2 == 0:
        raise ValueError("Kernel size must be odd")
    
    if gray:
        gray = cv2.cvtColor(photo, cv2.COLOR_BGR2GRAY)
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=kernel_size)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=kernel_size)
        segmented_image = cv2.addWeighted(cv2.convertScaleAbs(sobelx), 0.5, cv2.convertScaleAbs(sobely), 0.5, 0)
    else:
        sobelx = cv2.Sobel(photo, cv2.CV_64F, 1, 0, ksize=kernel_size)
        sobely = cv2.Sobel(photo, cv2.CV_64F, 0, 1, ksize=kernel_size)
        segmented_image = cv2.addWeighted(cv2.convertScaleAbs(sobelx), 0.5, cv2.convertScaleAbs(sobely), 0.5, 0)
    return segmented_image

def segment_region_growing(image, seed_point: list, threshold=10):
    # Inicjalizacja rozmiarów obrazu i tworzenie macierzy oznaczającej przynależność do regionu
    height, width, channels = image.shape
    segmented_region = np.zeros((height, width), np.bool_)

    # Lista pikseli do sprawdzenia, zaczynamy od punktu startowego
    pixels_to_check = [seed_point]
    # Wartość intensywności pikseli startowego dla wszystkich kanałów
    seed_value = image[seed_point[0], seed_point[1], :]

    while len(pixels_to_check) > 0:
        # Pobieramy obecny piksel do sprawdzenia
        current_pixel = pixels_to_check.pop(0)
        x, y = current_pixel[0], current_pixel[1]

        # Jeśli już odwiedzony, kontynuujemy
        if segmented_region[x, y]:
            continue

        # Sprawdzamy, czy obecny piksel spełnia kryterium dla każdego kanału RGB
        if np.all(np.abs(image[x, y, :] - seed_value) <= threshold):
            # Jeśli tak, dodajemy do regionu
            segmented_region[x, y] = True

            # Sprawdzamy sąsiednie piksele w czterech kierunkach
            if x > 0 and not segmented_region[x - 1, y]:
                pixels_to_check.append((x - 1, y))
            if x < height - 1 and not segmented_region[x + 1, y]:
                pixels_to_check.append((x + 1, y))
            if y > 0 and not segmented_region[x, y - 1]:
                pixels_to_check.append((x, y - 1))
            if y < width - 1 and not segmented_region[x, y + 1]:
                pixels_to_check.append((x, y + 1))

    return segmented_region

def segment_watershed(image): 

    # Załóżmy, że na wejściu jest obraz RGB, więc konwersja do skali szarości
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

    # Redukcja szumów za pomocą rozmycia Gaussa
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Wykonanie progowania Otsu
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Utworzenie obrazu z markerami za pomocą operacji morfologicznych
    kernel = np.ones((3, 3), np.uint8)
    sure_bg = cv2.dilate(binary, kernel, iterations=3)
    
    # Użycie operacji odległościowej, aby znaleźć pewne obszary tła
    dist_transform = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    _, sure_fg = cv2.threshold(dist_transform, 0.7 * dist_transform.max(), 255, 0)

    # Znalezienie niepewnych obszarów (obszarów brzegowych)
    sure_fg = np.uint8(sure_fg)
    unknown = cv2.subtract(sure_bg, sure_fg)

    # Oznaczenie markerów dla Watershed
    _, markers = cv2.connectedComponents(sure_fg)
    markers = markers + 1
    markers[unknown == 255] = 0

    # Zastosowanie algorytmu Watershed
    cv2.watershed(image, markers)
    image[markers == -1] = [0, 0, 255]  # Oznaczenie konturów na czerwono

    # Zwrócenie wyniku
    return image

def use_MiDaS(image, model_type = "MiDaS_small"):
    #model_type = "DPT_ Large"
    # model_type = "DPT_Hybrid"
    model_type = "MiDaS_small"

    midas = torch.hub.load("intel-isl/MiDaS", model_type)

    device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
    midas.to(device)
    midas.eval()

    midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")

    if model_type == "DPT_Large" or model_type == "DPT_Hybrid": transform = midas_transforms.dpt_transform
    else: transform = midas_transforms.small_transform

    input_batch = transform(image).to(device)

    with torch.no_grad():
        prediction = midas(input_batch)

        prediction = torch.nn.functional.interpolate(
            prediction.unsqueeze(1),
            size=image.shape[:2],
            mode="bicubic",
            align_corners=False,
        ).squeeze()

    return prediction.cpu().numpy()

def use_EVP(image): #TODO: do naprawy XDD
    # Use a pipeline as a high-level helper
    evp = AutoModel.from_pretrained("MykolaL/evp_depth", trust_remote_code=True)

    transform = transforms.ToTensor()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    image = transform(image).unsqueeze(0).to(device)
    evp = evp.to(device)
    depth = evp(image)

    return depth

def use_DeepLabV3(image): #TODO: check
    model = torch.hub.load('pytorch/vision:v0.9.0', 'deeplabv3_resnet101', pretrained=True)
    model.eval()

    transform = torch.hub.load('pytorch/vision:v0.9.0', 'transforms', pretrained=True)

    input_tensor = transform(image).unsqueeze(0)

    with torch.no_grad():
        output = model(input_tensor)['out'][0]
        output_predictions = output.argmax(0)

    return output_predictions

def use_OneFormer(image, task = 'semantic'): 
    '''
        Function takes an image and returns segmented image using OneFormer model.
        :param image: image to segment
        :param task: 'semantic', 'instance' or 'panoptic'
    '''
    # https://huggingface.co/docs/transformers/main/en/model_doc/oneformer#transformers.OneFormerForUniversalSegmentation
    processor = OneFormerProcessor.from_pretrained("shi-labs/oneformer_ade20k_swin_tiny")
    model = OneFormerForUniversalSegmentation.from_pretrained("shi-labs/oneformer_ade20k_swin_tiny")
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = cv2.resize(image, (224, 224))
    plt.imshow(image)
    plt.show()

    #image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    if isinstance(image.size, int):
        image_size = (image.size, image.size)  # lub inna odpowiednia wartość
    else:
        image_size = image.size[::-1]

    print(torch.cuda.is_available())


    if task == 'semantic':
        input_tensor = processor(image,['semantic'], return_tensors="pt")
        output = model(**input_tensor)
        #print(output)

        #class_queries_logits = output.logits
        #masks_queries_logits = output.masks_queries_logits
        predicted_semantic_map = processor.post_process_semantic_segmentation(output, target_sizes=[image_size])[0]
        return predicted_semantic_map

    elif task == 'instance':
        input_tensor = processor(image, ["instance"], return_tesnor="pt")
        output = model(**input_tensor)

        #class_queries_logits = output.class_queries_logits
        #masks_queries_logits = output.masks_queries_logits
        predicted_instance_map = processor.post_process_instance_segmentation(output, target_sizes=[image_size])[0]["segmentation"]
        return predicted_instance_map

    elif task == 'panoptic':
        input_tensor = processor(image, ["panoptic"], return_tensors="pt")
        output = model(**input_tensor)

        #class_queries_logits = output.class_queries_logits
        #masks_queries_logits = output.masks_queries_logits
        predicted_panoptic_map = processor.post_process_panoptic_segmentation(output, target_sizes=[image_size])[0]["segmentation"]        
        return predicted_panoptic_map
    
def use_BEiT(image):
    #https://huggingface.co/docs/transformers/main/en/model_doc/beit#transformers.BeitForImageClassification

    '''
    '''

    image_processor = AutoImageProcessor.from_pretrained("microsoft/beit-base-finetuned-ade-640-640")
    model = BeitForSemanticSegmentation.from_pretrained("microsoft/beit-base-finetuned-ade-640-640")

    input = image_processor(images=image, return_tensors="pt")
    output = model(**input)

    logits = output.logits
    predicted_segmentation = torch.argmax(logits, dim=1).squeeze().cpu().numpy()

    return predicted_segmentation, logits

def use_SegFormer(image):
    #https://huggingface.co/nvidia/segformer-b0-finetuned-ade-512-512

    # from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation
    # from PIL import Image``
    # import requests

    # processor = SegformerImageProcessor.from_pretrained("nvidia/segformer-b0-finetuned-ade-512-512")
    # model = SegformerForSemanticSegmentation.from_pretrained("nvidia/segformer-b0-finetuned-ade-512-512")

    # url = "http://images.cocodataset.org/val2017/000000039769.jpg"
    # image = Image.open(requests.get(url, stream=True).raw)

    # inputs = processor(images=image, return_tensors="pt")
    # outputs = model(**inputs)
    # logits = outputs.logits  # shape (batch_size, num_labels, height/4, width/4)

    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = cv2.resize(image, (512, 512))

    processor = SegformerImageProcessor.from_pretrained("nvidia/segformer-b0-finetuned-ade-512-512")
    model = SegformerForSemanticSegmentation.from_pretrained("nvidia/segformer-b0-finetuned-ade-512-512")

    input = processor(images=image, return_tensors="pt")
    output = model(**input)
    logits = output.logits

    predicted_segmentation = torch.argmax(logits, dim=1).squeeze().cpu().numpy()
    return predicted_segmentation, logits
    
