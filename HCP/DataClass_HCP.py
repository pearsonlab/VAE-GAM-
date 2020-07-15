"""
Script defining fMRIDataset Class and loaders to be used
Pretty much same as in checker set

Major Change:
- Took out age and sex stuff which is NOT needed
- Eventually will merge both and keep a universal DataClass

ToDos
Add proper train/test split and better random shuffling here...

"""
import torch
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
import nibabel as nib

class FMRIDataset(Dataset):
    """This is a slightly different version from Rachel's original """
    def __init__(self, csv_file, transform= None):
        self.df = pd.read_csv(csv_file)
        self.transform = transform
    def __len__(self):
        """Return the number of samples in dset"""
        return len(self.df)
    def __getitem__(self, idx):
        """Returns a single sample from dset
           Each sample is a dict w/ following keys:
           subjid: unique index for each subj. These repeat across vols for same subj.
           subj: actual string defining a subj identifier
           volume: np array containing one volume from a given subj
           task: real-valued task  -- after HRF convolved
           task_bin: binary task var (needed for other things)
           trans_x, trans_y, trans_z: translation in x, y, z axis respectively
           rot_x, rot_y, rot_z: rotation across 3 axis (same as canonical defs for fMRI)
        """
        #get subjid and its index
        unique_subjs = self.df.subjid.unique().tolist()
        subjid = self.df.iloc[idx,1]
        subj_idx = unique_subjs.index(subjid)
        #get all other covariates
        #vol # and nii path
        vol_num = self.df.iloc[idx,2]
        nii = self.df.iloc[idx,3]
        #convolved and binary task variables
        task = self.df.iloc[idx,4]
        task_bin = self.df.iloc[idx,5]
        #motion params
        trans_x = self.df.iloc[idx,6]
        trans_y = self.df.iloc[idx,7]
        trans_z = self.df.iloc[idx,8]
        rot_x = self.df.iloc[idx,9]
        rot_y = self.df.iloc[idx,10]
        rot_z = self.df.iloc[idx,11]

        fmri = np.array(nib.load(nii).dataobj)
        # need to get max for this dset here!!!
        # do we wish to scale individual dsets??
        max = 40020.754
        volume = fmri[:,:,:,vol_num]
        flat_vol = volume.flatten()
        norm_vol = np.true_divide(flat_vol, max).reshape(41,49,35)
        #added vol_num to sample
        sample = {'subjid': subj_idx, 'volume': norm_vol, 'vol_num':vol_num,
                  'task':task,'subj': subjid, 'task_bin':task_bin,
                  'trans_x':trans_x, 'trans_y':trans_y, 'trans_z':trans_z,
                  'rot_x':rot_x, 'rot_y':rot_y, 'rot_z':rot_z}
        if self.transform:
            sample = self.transform(sample)

        return(sample)

class ToTensor(object):
    "Converts sample arrays to tensors"

    def __call__(self, sample):
        subjid, volume, vol_num = sample['subjid'], sample['volume'], sample['vol_num']
        #Concat task w/ mot params by row
        #vol_num is NOT needed!!!
        #clean this out in original ...
        covars = np.array([sample['task'], sample['trans_x'], sample['trans_y'], sample['trans_z'], \
        sample['rot_x'], sample['rot_y'], sample['rot_z']], dtype=np.float64)
        return{'covariates':torch.from_numpy(covars).float(),
                'volume': torch.from_numpy(volume).float(),
                'subjid': torch.tensor(subjid, dtype=torch.int64),
                'vol_num': torch.tensor(vol_num, dtype=torch.float64)}

def setup_data_loaders(batch_size=32, shuffle=(True, False), csv_file=''):
    #Set num workers to zero to avoid runtime error msg.
    #This might need further looking into when we use larger dsets.
    #Setup the train loaders.
    train_dataset = FMRIDataset(csv_file = csv_file, transform = ToTensor())
    train_loader = DataLoader(train_dataset, batch_size=batch_size, \
                              shuffle=shuffle[0], num_workers=0)
    # Setup the test loaders.
    test_dataset = FMRIDataset(csv_file = csv_file, transform = ToTensor())
    test_loader = DataLoader(test_dataset, batch_size=batch_size, \
                             shuffle=shuffle[1], num_workers=0)
    return {'train':train_loader, 'test':test_loader}