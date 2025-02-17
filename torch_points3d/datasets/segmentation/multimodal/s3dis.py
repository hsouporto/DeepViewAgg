import torch
import json
from torch_points3d.datasets.base_dataset_multimodal import BaseDatasetMM
from torch_points3d.datasets.segmentation.s3dis import *
from torch_geometric.data import Data
from torch_points3d.core.multimodal.data import MMData
from torch_points3d.core.data_transform.multimodal.image import \
    SelectMappingFromPointId
from .utils import read_image_pose_pairs, img_info_to_img_data

########################################################################
#                             S3DIS Utils                              #
########################################################################

# Images that are located outside of the point clouds and for which we
# therefore cannot recover a trustworthy projection with occlusions
S3DIS_OUTSIDE_IMAGES = [
    # Area 1
    "camera_f62548d255d24e6983b698e34b343b60_hallway_8_frame_equirectangular_domain",
    "camera_78d716cac81c4b0d85a90927b159b77e_hallway_4_frame_equirectangular_domain",
    "camera_95fab66e5ca643cc97aaab4647f145e3_hallway_5_frame_equirectangular_domain",
    "camera_684b940fafd64fd98aef16157c8a96e2_hallway_5_frame_equirectangular_domain",
    "camera_24f42d6efff54b09a34897f69fa11064_hallway_5_frame_equirectangular_domain",
    "camera_e0c041d3b2a94769b1dc86935f983f34_WC_1_frame_equirectangular_domain",
    "camera_1edba7eece574027bab1fa5459fd8cd4_WC_1_frame_equirectangular_domain",

    # Area 2
    "camera_b1d0a684de5d4412bae05b5da4bd6058_conferenceRoom_1_frame_equirectangular_domain",
    "camera_e0acda5a8a544aa8bf575ff0b1cc4557_conferenceRoom_1_frame_equirectangular_domain",
    "camera_76f70ab0399b4062a8a174dac4a5b5d4_hallway_5_frame_equirectangular_domain",
    "camera_087a5c7a06ac47db91f0b3239b9a568c_hallway_5_frame_equirectangular_domain",
    "camera_c87ef2a2ea404851a1ed515e39c19ebc_hallway_12_frame_equirectangular_domain",

    # Area 3
    "camera_1672a6a767af4676a441d2872752d6b5_office_10_frame_equirectangular_domain",
    "camera_711a8a2f5d1c477da742bddfe3b6c15a_office_10_frame_equirectangular_domain",
    "camera_fed3d2b0206b428d836acd7d7a44f85b_office_9_frame_equirectangular_domain",
    "camera_83f59b29737047b9a139cebb8612803d_office_9_frame_equirectangular_domain",
    "camera_274fa02e9d7748589a4a3171fdc148cc_office_10_frame_equirectangular_domain",
    "camera_ede7064adbbe490284373cf8c0cf8bae_lounge_2_frame_equirectangular_domain",
    "camera_d911682267cf458a87bdfe2fbd491c46_lounge_2_frame_equirectangular_domain",
    "camera_1c029f7dc23548cab4ac62429f96eb76_lounge_2_frame_equirectangular_domain",

    # Area 4
    "camera_21d093553b30417e80f382f09ff9173c_hallway_1_frame_equirectangular_domain",
    "camera_b9eca4fa258e4160823cf6b1da447c8f_hallway_1_frame_equirectangular_domain",
    "camera_887c83e5e56d4b4db6867ea493615ada_lobby_1_frame_equirectangular_domain",
    "camera_161eb799efd24b548a8760ae98a16736_lobby_1_frame_equirectangular_domain",
    "camera_3f70cae87b464ef9a9ad9a1b6118e8c1_lobby_1_frame_equirectangular_domain",
    "camera_927a307dc7f5439faae8c42a35aa6e4c_lobby_1_frame_equirectangular_domain",
    "camera_39e8345836e64d8d9d3bacde37f5ee12_hallway_2_frame_equirectangular_domain",
    "camera_0e47c7ac0bfe4720bfff75f1a24cfb56_office_19_frame_equirectangular_domain",

    # Area 6
    "camera_7edd2f07f6be4b25bcc4b3bf330146ff_hallway_6_frame_equirectangular_domain",
    "camera_af9f94170d54489d97d974a9cca06856_hallway_6_frame_equirectangular_domain",
    "camera_247d69e9f0e64242a9330d70eca2ab0c_hallway_6_frame_equirectangular_domain",
    "camera_932e85d85fd74cbb8c9e9e818e250a98_hallway_6_frame_equirectangular_domain",
    "camera_29d9a627823449bb8df926f6ee29d946_hallway_6_frame_equirectangular_domain",
    "camera_d1763aa9c28546efa570296046d7be26_hallway_6_frame_equirectangular_domain",
    "camera_051e24918e884291aebf022719ad572a_office_23_frame_equirectangular_domain",
    "camera_a642c69e7dec4c98aacc3595f1259b03_hallway_2_frame_equirectangular_domain",
    "camera_cff198550a97439eae623dd55452c4c0_hallway_2_frame_equirectangular_domain",
    "camera_5917b1f08a0143b0994d8b3946d02343_hallway_2_frame_equirectangular_domain",
    "camera_629e301c74124597bd41c2ebe4b791b7_hallway_2_frame_equirectangular_domain",
    "camera_8c334635cf8147549ddce70664d70a12_office_23_frame_equirectangular_domain",
    "camera_699cc3c1b5084f828605bcfc8ed8264d_office_23_frame_equirectangular_domain",
    "camera_76b92c8b42e844759a4561f3e67e1007_office_23_frame_equirectangular_domain",
    "camera_d3e9dda66f31417c99c2d346b1797ebd_office_23_frame_equirectangular_domain",
    "camera_49e8cb6e01a448809a7eda23eeb9d4e2_hallway_2_frame_equirectangular_domain",
    "camera_87ea116ead10458e85a923d54be70fcb_hallway_2_frame_equirectangular_domain"]


# ----------------------------------------------------------------------

def read_s3dis_pose(json_file):
    # Area 5b poses need a special treatment
    # Need to see the file comes from Area i in the provided filepath
    area_5b = 'area_5b' in json_file.lower()

    # Loading the Stanford pose json file
    with open(json_file) as f:
        pose_data = json.load(f)

    # XYZ camera position
    xyz = np.array(pose_data['camera_location'])

    # Omega, Phi, Kappa camera pose
    # We define a different pose coordinate system 
    omega, phi, kappa = [np.double(i)
                         for i in pose_data['final_camera_rotation']]
    #     opk = np.array([omega - (np.pi / 2), -phi, -kappa])
    opk = np.array([omega - (np.pi / 2), -phi, -kappa - (np.pi / 2)])

    # Area 5b poses require some rotation and offset corrections
    if area_5b:
        M = np.array([[0, 1, 0],
                      [-1, 0, 0],
                      [0, 0, 1]])
        xyz = M.dot(xyz) + np.array([-4.10, 6.25, 0.0])
        opk = opk + np.array([0, 0, np.pi / 2])

    return {'xyz': xyz, 'opk': opk}


# ----------------------------------------------------------------------

def s3dis_image_area(path):
    """S3DIS-specific. Recover the area from the image path."""
    return path.split('/')[-4]


# ----------------------------------------------------------------------

def s3dis_image_room(path):
    """S3DIS-specific. Recover the room from the image path."""
    return '_'.join(os.path.basename(path).split('_')[2:4])


# ----------------------------------------------------------------------

def s3dis_image_name(path):
    """S3DIS-specific. Recover the name from the image path."""
    return os.path.basename(path).split('_')[1]


########################################################################
#                     S3DIS Torch Geometric Dataset                    #
########################################################################

class S3DISOriginalFusedMM(InMemoryDataset):
    """
    Multimodal extension of S3DISOriginalFused from 
    torch_points3d.datasets.segmentation.s3dis to 3D with images.
    """

    form_url = \
        "https://docs.google.com/forms/d/e/1FAIpQLScDimvNMCGhy_rmBA2g" \
        "HfDu3naktRm6A8BPwAWWDv-Uhm6Shw/viewform?c=0&w=1"
    download_url = \
        "https://drive.google.com/uc?id=0BweDykwS9vIobkVPN0wzRzFwTDg&" \
        "export=download"
    zip_name = "Stanford3dDataset_v1.2_Version.zip"
    patch_file = osp.join(DIR, "s3dis.patch")
    file_name = "Stanford3dDataset_v1.2"
    folders = [f"Area_{i}" for i in range(1, 7)]
    num_classes = S3DIS_NUM_CLASSES

    def __init__(
            self, root, test_area=6, split="train", transform=None,
            pre_transform=None, pre_collate_transform=None, pre_filter=None,
            keep_instance=False, pre_transform_image=None, transform_image=None,
            img_ref_size=(512, 256), verbose=False, debug=False):
        assert test_area in list(range(1, 7))

        self.transform = transform
        self.pre_collate_transform = pre_collate_transform
        self.pre_transform_image = pre_transform_image
        self.transform_image = transform_image
        self.img_ref_size = img_ref_size
        self.test_area = test_area
        self.keep_instance = keep_instance
        self.verbose = verbose
        self.debug = debug
        self._split = split

        super(S3DISOriginalFusedMM, self).__init__(
            root, transform, pre_transform, pre_filter)

        if split == "train":
            path = self.processed_paths[0]
        elif split == "val":
            path = self.processed_paths[1]
        elif split == "test":
            path = self.processed_paths[2]
        elif split == "trainval":
            path = self.processed_paths[3]
        else:
            raise ValueError(
                f"Split {split} found, but expected either train, val,"
                f" trainval or test")

        self._load_data(path)

        if split == "test":
            self.raw_test_data = torch.load(self.raw_areas_paths[test_area - 1])

    @property
    def center_labels(self):
        if hasattr(self.data, "center_label"):
            return self.data.center_label
        else:
            return None

    @property
    def raw_file_names(self):
        return self.folders

    @property
    def image_dir(self):
        return osp.join(self.root, 'image')

    @property
    def pre_processed_path(self):
        pre_processed_file_names = "preprocessed.pt"
        return osp.join(self.processed_dir, pre_processed_file_names)

    @property
    def pre_collated_path(self):
        pre_collated_path_name = "pre_collate.pt"
        return osp.join(self.processed_dir, pre_collated_path_name)

    @property
    def image_data_path(self):
        return osp.join(self.processed_dir, "image_data.pt")

    @property
    def pre_transformed_image_path(self):
        return osp.join(self.processed_dir, "pre_transform_image.pt")

    @property
    def raw_areas_paths(self):
        return [osp.join(self.processed_dir, "raw_area_%i.pt" % i)
                for i in range(6)]

    @property
    def processed_file_names(self):
        test_area = self.test_area
        return (
                [f"{s}_{test_area}.pt"
                 for s in ["train", "val", "test", "trainval"]]
                + self.raw_areas_paths
                + [self.pre_processed_path])

    @property
    def intermediate_processed_paths(self):
        return [
            self.pre_processed_path,
            self.pre_collated_path,
            self.image_data_path,
            self.pre_transformed_image_path]

    @property
    def raw_test_data(self):
        return self._raw_test_data

    @raw_test_data.setter
    def raw_test_data(self, value):
        self._raw_test_data = value

    def download(self):
        raw_folders = os.listdir(self.raw_dir)
        if len(raw_folders) == 0:
            if not osp.exists(osp.join(self.root, self.zip_name)):
                # TODO: download and unzip images. Create a custom
                #  repository with only RGB images and poses ?
                """
                Expected image directory structure:
                root
                |___images
                    |___area_{1, 2, 3, 4, 5a, 5b, 6}
                        |___pano
                            |___depth
                                |___image_name_depth.png
                            |___normal
                                |___image_name_normals.json
                            |___pose
                                |___image_name_pose.json
                            |___rgb
                                |___image_name_rgb.png
                            |___semantic
                                |___image_name_semantic.json
                            |___semantic_pretty
                                |___image_name_semantic_pretty.json
                """
                log.info("WARNING: You are downloading S3DIS dataset")
                log.info(f"Please, register yourself by filling up the form "
                         f"at {self.form_url}")
                log.info("***")
                log.info("Press any key to continue, or CTRL-C to exit. By "
                         "continuing, you confirm filling up the form.")
                input("")
                gdown.download(
                    self.download_url, osp.join(self.root, self.zip_name),
                    quiet=False)
            extract_zip(osp.join(self.root, self.zip_name), self.root)
            shutil.rmtree(self.raw_dir)
            os.rename(osp.join(self.root, self.file_name), self.raw_dir)
            shutil.copy(self.patch_file, self.raw_dir)
            cmd = f"patch -ruN -p0 -d  {self.raw_dir} < " \
                  f"{osp.join(self.raw_dir, 's3dis.patch')}"
            os.system(cmd)
        else:
            intersection = len(set(self.folders).intersection(set(raw_folders)))
            if intersection != 6:
                shutil.rmtree(self.raw_dir)
                os.makedirs(self.raw_dir)
                self.download()

    def process(self):
        # --------------------------------------------------------------
        # Initialize the chain of intermediate processing files
        # If a file in the chain is not found, all subsequent files are
        # removed to ensure a clean preprocessing computation
        # --------------------------------------------------------------
        for i, p in enumerate(self.intermediate_processed_paths):
            if not osp.exists(p):
                list(map(lambda path: (os.remove(path) if osp.exists(path)
                                       else None),
                         self.intermediate_processed_paths[i + 1:]))
                break

        # --------------------------------------------------------------
        # Preprocess 3D data
        # Download, pre_transform and pre_filter raw 3D data
        # --------------------------------------------------------------
        if not osp.exists(self.pre_processed_path):
            print('Preprocessing the raw 3D data...')

            data_files = [
                (f, room_name, osp.join(self.raw_dir, f, room_name))
                for f in self.folders
                for room_name in os.listdir(osp.join(self.raw_dir, f))
                if osp.isdir(osp.join(self.raw_dir, f, room_name))]

            # Gather all data from each area in a List(List(Data))
            data_list = [[] for _ in range(6)]
            for (area, room_name, file_path) in tq(data_files):
                area_num = int(area[-1]) - 1
                if self.debug:
                    read_s3dis_format(
                        file_path, room_name, label_out=True,
                        verbose=self.verbose, debug=self.debug)
                    continue
                else:
                    xyz, rgb, labels, instance_labels, _ = read_s3dis_format(
                        file_path, room_name, label_out=True,
                        verbose=self.verbose, debug=self.debug)

                    # Room orientation correction
                    # 2 rooms need to be rotated by 180° around Z:
                    #   - Area_2/hallway_11
                    #   - Area_5/hallway_6
                    if (area_num == 1 and room_name == 'hallway_11') or \
                            (area_num == 4 and room_name == 'hallway_6'):
                        xy_center = (xyz[:, 0:2].max(dim=0)[0]
                                     + xyz[:, 0:2].min(dim=0)[0]) / 2
                        # 180° Z-rotation around the XY-center
                        xyz[:, 0:2] = 2 * xy_center - xyz[:, 0:2]

                    rgb_norm = rgb.float() / 255.0
                    data = Data(pos=xyz, y=labels, rgb=rgb_norm)

                    if room_name in VALIDATION_ROOMS:
                        data.is_val = torch.ones(data.num_nodes, dtype=bool)
                    else:
                        data.is_val = torch.zeros(data.num_nodes, dtype=bool)

                    if self.keep_instance:
                        data.instance_labels = instance_labels

                    if self.pre_filter is not None \
                            and not self.pre_filter(data):
                        continue

                    data_list[area_num].append(data)

            # Save raw areas
            raw_areas = cT.PointCloudFusion()(data_list)
            for i, area in enumerate(raw_areas):
                delattr(area, 'is_val')
                torch.save(area, self.raw_areas_paths[i])

            # Pre-transform
            if self.pre_transform is not None:
                data_list = [
                    [self.pre_transform(data) for data in area_data]
                    for area_data in data_list]

            # Save the data into one big 'preprocessed.pt' file 
            torch.save(data_list, self.pre_processed_path)

        else:
            # Recover the per-area Data list from the 'preprocessed.pt'
            # file
            print('Loading the preprocessed 3D data...')
            data_list = torch.load(self.pre_processed_path)

        print('Done\n')

        if self.debug:
            return

        # --------------------------------------------------------------
        # Pre-collate 3D data
        # Build the data splits and pre_collate them
        # --------------------------------------------------------------
        if not osp.exists(self.pre_collated_path):

            # Run the pre_collate_transform to finalize the data
            # preparation. Among other things, the 'origin_id' and
            # 'mapping_index' are generated here
            if self.pre_collate_transform:
                print('Running pre-collate on 3D data...')
                log.info("pre_collate_transform ...")
                log.info(self.pre_collate_transform)
                data_list = self.pre_collate_transform(data_list)

            # Save the pre_collated data
            torch.save(data_list, self.pre_collated_path)

        else:
            # Recover data from the 'pre_collated.pt' file
            print('Loading the pre-collated 3D data...')
            data_list = torch.load(self.pre_collated_path)

        print('Done\n')

        # --------------------------------------------------------------
        # Recover image data
        # --------------------------------------------------------------
        if not osp.exists(self.image_data_path):
            print('Computing image data...')
            rooms = [
                (int(f[-1]) - 1, room_name)
                for f in self.folders
                for room_name in os.listdir(osp.join(self.raw_dir, f))
                if osp.isdir(osp.join(self.raw_dir, f, room_name))]
            rooms = [[r[1] for r in rooms if r[0] == i] for i in range(6)]

            image_data_list = []
            for i in range(6):

                # S3DIS Area 5 images are split into two folders
                # 'area_5a' and 'area_5b' and one of them requires
                # specific treatment for pose reading
                folders = [f"area_{i + 1}"] if i != 4 \
                    else ["area_5a", "area_5b"]

                image_info_list = [
                    {'path': i_file, **read_s3dis_pose(p_file)}
                    for folder in folders
                    for i_file, p_file in read_image_pose_pairs(
                        osp.join(self.image_dir, folder, 'pano', 'rgb'),
                        osp.join(self.image_dir, folder, 'pano', 'pose'),
                        skip_names=S3DIS_OUTSIDE_IMAGES)]

                # Dropping image info for images outside of rooms found
                # during preprocessing
                image_info_list = [
                    x for x in image_info_list
                    if s3dis_image_room(x['path']) in rooms[i]]

                print(f"    Area {i + 1} - {len(rooms[i])} rooms - "
                      f"{len(image_info_list)} images")

                # Keep all images for the test area
                image_data_list.append(img_info_to_img_data(image_info_list, self.img_ref_size))

            # Save image data
            torch.save(image_data_list, self.image_data_path)

        else:
            print('Loading the image data...')
            image_data_list = torch.load(self.image_data_path)

        print('Done\n')

        # --------------------------------------------------------------
        # Pre-transform image data
        # This is where images are loaded and mappings are computed
        # --------------------------------------------------------------
        if not osp.exists(self.pre_transformed_image_path):
            print('Running the image pre-transforms...')
            mm_data_list = (data_list, image_data_list)
            if self.pre_transform_image:
                mm_data_list = self.pre_transform_image(*mm_data_list)
            torch.save(mm_data_list, self.pre_transformed_image_path)

        else:
            print('Loading the image pre-transformed data...')
            mm_data_list = torch.load(self.pre_transformed_image_path)

        print('Done\n')

        # --------------------------------------------------------------
        # Compute train / val / test / trainval splits
        # This is where the 'train_i.pt', 'val_i.pt', etc. are created
        # --------------------------------------------------------------
        print(f'Computing and saving train, val, test and trainval '
              f'splits for test_area=Area_{self.test_area}...')

        # Save test split preprocessed multimodal data
        test_mm_data_list = tuple([x.pop(self.test_area - 1)
                                   for x in mm_data_list])
        delattr(test_mm_data_list[0], 'is_val')
        torch.save(test_mm_data_list, self.processed_paths[2])
        del test_mm_data_list

        # Save trainval preprocessed multimodal data
        # NB: only trainval data remains in mm_data_list after popping
        #  test data out of it
        is_val_list = [data.is_val for data in mm_data_list[0]]
        for data in mm_data_list[0]:
            delattr(data, 'is_val')
        torch.save(mm_data_list, self.processed_paths[3])

        # Local helper to index a Data object with a torch.Tensor
        def indexer(data, idx):
            data_ = data.clone()
            for key, item in data:
                if torch.is_tensor(item) and item.size(0) == data.num_nodes:
                    data_[key] = data_[key][idx]
            return data_

        # Extract and save train preprocessed multimodal data
        transform = SelectMappingFromPointId()
        data = [indexer(d, ~is_val) for d, is_val
                in zip(mm_data_list[0], is_val_list)]
        images = [im.clone() for im in mm_data_list[1]]
        torch.save(transform(data, images), self.processed_paths[0])

        # Extract and save val preprocessed multimodal data
        data = [indexer(d, is_val) for d, is_val
                in zip(mm_data_list[0], is_val_list)]
        torch.save(transform(data, mm_data_list[1]), self.processed_paths[1])
        del mm_data_list

        print('Done\n')

    def _load_data(self, path):
        self.data, self.images = torch.load(path)

    # TODO: this overwrites `torch_geometric.data.InMemoryDataset.indices`
    #  so that we can handle `torch_geometric>=1.6`. This dirty trick, in
    #  return, was needed to use `torch>=1.8`, which we needed to access
    #  the new torch profiler. In the long run, need to make TP3D
    #  compatible with `torch_geometric>=2.0.0`
    def indices(self):
        import torch_geometric as pyg
        version = pyg.__version__.split('.')
        is_new_pyg = int(version[0]) >= 2 or int(version[1]) >= 7
        if is_new_pyg:
            return range(len(self)) if self._indices is None else self._indices
        return super().indices()


# ----------------------------------------------------------------------

class S3DISSphereMM(S3DISOriginalFusedMM):
    """ Small variation of S3DISOriginalFused that allows random
    sampling of spheres within an Area during training and validation.
    By default, spheres have a radius of 2m and are taken on a
    20cm regular grid. If `sample_per_epoch > 0`, indexing the dataset
    will return random spheres picked on the grid with a bias towards
    balancing class frequencies. Otherwise, if `sample_per_epoch <= 0`
    indexing the dataset becomes deterministic and will return spheres
    of corresponding indices.

    http://buildingparser.stanford.edu/dataset.html

    Parameters
    ----------
    root: str
        Path to the directory where the data will be saved
    test_area: int
        Number between 1 and 6 that denotes the area used for testing
    train: bool
        Is this a train split or not
    pre_collate_transform:
        Transforms to be applied before the data is assembled into
        samples (apply fusing here for example)
    keep_instance: bool
        Set to True if you wish to keep instance data
    sample_per_epoch : int
        Number of spheres that are randomly sampled at each epoch (-1
        for fixed grid)
    radius : float
        Radius of each sphere
    sample_res : float
        The resolution of the regular grid on which the dataset samples
        will be picked
    pre_transform
    transform
    pre_filter
    """

    def __init__(
            self, root, *args, sample_per_epoch=100, radius=2, sample_res=2,
            **kwargs):
        self._sample_per_epoch = sample_per_epoch
        self._sample_res = sample_res
        self._radius = radius
        self._grid_sphere_sampling = cT.GridSampling3D(size=sample_res)
        super().__init__(root, *args, **kwargs)

    def __len__(self):
        if self._sample_per_epoch > 0:
            return self._sample_per_epoch
        else:
            return len(self._test_spheres)

    def __getitem__(self, idx):
        """
        Indexing mechanism for the Dataset. Only supports int indexing.

        Overwrites the torch_geometric.InMemoryDataset.__getitem__()
        used for indexing Dataset. Extends its mechanisms to multimodal
        data.

        Get a 3D points Data sphere sample with image mapping
        attributes, along with the list idx.
        """
        assert isinstance(idx, int), \
            f"Indexing with {type(idx)} is not supported, only " \
            f"{int} are accepted."

        # Get the 3D point sample and apply transforms
        i_area, data = self.get(self.indices()[idx])
        data = data if self.transform is None else self.transform(data)

        # Get the corresponding images and mappings
        data, images = self.transform_image(data, self._images[i_area].clone())

        return MMData(data, image=images)

    def get(self, idx):
        """
        Get a 3D points Data sample. Does not return multimodal
        attributes.

        Overwrites the torch_geometric.InMemoryDataset.get(), which is
        called from inside the
        torch_geometric.InMemoryDataset.__getitem__() used for indexing
        datasets.
        """
        if self._sample_per_epoch > 0:
            # For train datasets
            # Return a random spherical sample and the associated area
            # id
            return self._get_random()
        else:
            # For test and val datasets
            # Return the precomputed sphere at idx and the associated
            # area id
            test_sphere = self._test_spheres[idx].clone()
            i_area = test_sphere.area_id
            delattr(test_sphere, 'area_id')
            return i_area, test_sphere

    def process(self):
        # We have to include this method, otherwise the parent class
        # skips processing.
        super().process()

    def download(self):
        # We have to include this method, otherwise the parent class
        # skips download.
        super().download()

    def _get_random(self):
        """
        S3DISSphereMM has predefined sphere centers accross all areas
        in the split. The _get_random method randomly picks a center
        and recovers the sphere-neighborhood for the appropriate
        S3DISSphereMM._datas[i_area].

        Called if S3DISSphereMM is NOT test set. 
        """
        # Random spheres biased towards getting more low frequency classes
        chosen_label = np.random.choice(self._labels, p=self._label_counts)
        valid_centres = self._centres_for_sampling[
            self._centres_for_sampling[:, 4] == chosen_label]
        centre_idx = int(random.random() * (valid_centres.shape[0] - 1))
        centre = valid_centres[centre_idx]
        i_area = centre[3].int()
        area_data = self._datas[i_area]
        sphere_sampler = cT.SphereSampling(
            self._radius, centre[:3], align_origin=False)
        return i_area, sphere_sampler(area_data)

    def _load_data(self, path):
        """
        Initializes the self._datas, self._images which hold all the
        preprocessed multimodal data in memory. Also initializes the
        sphere sampling centers and per-area KDTrees.
        
        Overwrites the S3DISOriginalFusedMM._load_data()
        """
        self._datas, self._images = torch.load(path)

        if not isinstance(self._datas, list):
            self._datas = [self._datas]
        if not isinstance(self._images, list):
            self._images = [self._images]

        if self._sample_per_epoch > 0:
            self._centres_for_sampling = []
            for i, data in enumerate(self._datas):
                # Just to make we don't have some out-of-date data in
                # there
                assert not hasattr(data, cT.SphereSampling.KDTREE_KEY)
                low_res = self._grid_sphere_sampling(data.clone())
                centres = torch.empty((low_res.pos.shape[0], 5),
                                      dtype=torch.float)
                centres[:, :3] = low_res.pos
                centres[:, 3] = i
                centres[:, 4] = low_res.y
                self._centres_for_sampling.append(centres)
                tree = KDTree(np.asarray(data.pos), leaf_size=10)
                setattr(data, cT.SphereSampling.KDTREE_KEY, tree)

            self._centres_for_sampling = torch.cat(
                self._centres_for_sampling, 0)
            uni, uni_counts = np.unique(
                np.asarray(self._centres_for_sampling[:, -1]),
                return_counts=True)
            uni_counts = np.sqrt(uni_counts.mean() / uni_counts)
            self._label_counts = uni_counts / np.sum(uni_counts)
            self._labels = uni

        else:
            # Save the area id in _test_spheres so we can recover
            # multimodal mappings after GridSphereSampling
            for i_area in range(len(self._datas)):
                self._datas[i_area].area_id = i_area
            grid_sampler = cT.GridSphereSampling(
                self._radius, grid_size=self._sample_res, center=False)
            self._test_spheres = grid_sampler(self._datas)


########################################################################
#                      S3DIS TP3D Dataset Wrapper                      #
########################################################################

class S3DISFusedDataset(BaseDatasetMM):
    """
    Wrapper around S3DISSphereMM that creates train and test datasets.

    http://buildingparser.stanford.edu/dataset.html

    Parameters
    ----------
    dataset_opt: omegaconf.DictConfig
        Config dictionary that should contain

            - dataroot
            - fold: test_area parameter
            - pre_collate_transform
            - train_transforms
            - test_transforms
    """

    INV_OBJECT_LABEL = INV_OBJECT_LABEL

    def __init__(self, dataset_opt):
        super().__init__(dataset_opt)

        sampling_format = dataset_opt.get('sampling_format', 'sphere')
        assert sampling_format == 'sphere', \
            f"Only sampling format 'sphere' is supported for now."

        sample_per_epoch = dataset_opt.get('sample_per_epoch', 3000)
        radius = dataset_opt.get('radius', 2)
        train_sample_res = dataset_opt.get('train_sample_res', radius / 10)
        eval_sample_res = dataset_opt.get('eval_sample_res', radius)
        train_is_trainval = dataset_opt.get('train_is_trainval', False)

        self.train_dataset = S3DISSphereMM(
            self._data_path,
            sample_per_epoch=sample_per_epoch,
            radius=radius,
            sample_res=train_sample_res,
            test_area=self.dataset_opt.fold,
            split="train" if not train_is_trainval else "trainval",
            pre_collate_transform=self.pre_collate_transform,
            transform=self.train_transform,
            pre_transform_image=self.pre_transform_image,
            transform_image=self.train_transform_image,
            img_ref_size=self.dataset_opt.resolution_2d)

        self.val_dataset = S3DISSphereMM(
            self._data_path,
            sample_per_epoch=-1,
            radius=radius,
            sample_res=eval_sample_res,
            test_area=self.dataset_opt.fold,
            split="val",
            pre_collate_transform=self.pre_collate_transform,
            transform=self.val_transform,
            pre_transform_image=self.pre_transform_image,
            transform_image=self.val_transform_image,
            img_ref_size=self.dataset_opt.resolution_2d)

        self.test_dataset = S3DISSphereMM(
            self._data_path,
            sample_per_epoch=-1,
            radius=radius,
            sample_res=eval_sample_res,
            test_area=self.dataset_opt.fold,
            split="test",
            pre_collate_transform=self.pre_collate_transform,
            transform=self.test_transform,
            pre_transform_image=self.pre_transform_image,
            transform_image=self.test_transform_image,
            img_ref_size=self.dataset_opt.resolution_2d)

        if dataset_opt.class_weight_method:
            self.add_weights(
                class_weight_method=dataset_opt.class_weight_method)

    @property
    def test_data(self):
        return self.test_dataset[0].raw_test_data

    @staticmethod
    def to_ply(pos, label, file):
        """
        Saves s3dis predictions to disk using s3dis color scheme.

        Parameters
        ----------
        pos : torch.Tensor
            tensor that contains the positions of the points
        label : torch.Tensor
            predicted label
        file : string
            Save location
        """
        to_ply(pos, label, file)

    def get_tracker(self, wandb_log: bool, tensorboard_log: bool):
        """Factory method for the tracker

        Arguments:
            wandb_log - Log using weight and biases
            tensorboard_log - Log using tensorboard
        Returns:
            [BaseTracker] -- tracker
        """
        from torch_points3d.metrics.s3dis_tracker import S3DISTracker

        return S3DISTracker(
            self, wandb_log=wandb_log, use_tensorboard=tensorboard_log)
