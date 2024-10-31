import cv2
import lib
import matplotlib.pyplot as plt
# import open3d as o3d


# color_image, depth_image = lib.get_rgb_and_depth_image()
# points_cloud = lib.get_point_cloud()


# fig = plt.figure()
# ax = fig.add_subplot(111, projection='3d')
# ax.scatter(points_cloud[:,0], points_cloud[:,1], points_cloud[:,2], s=10)

# ax.set_title("Chmura punktów")

# plt.show()

image = cv2.imread("./image.png")

image, labels, centers = lib.segment_knn(image, 10)
print(labels)
print(centers)

plt.imshow(image)
plt.show()

