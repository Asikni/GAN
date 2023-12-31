# -*- coding: utf-8 -*-
"""Generative_AI_Task.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/13pPdioMbnxrBhvPtOy2NLVrWML8b-G1Y

**Objective:**
Create a generative model to produce new content, such as text generation, image synthesis, or data augmentation.

####Image Generation using GANs.
"""

from google.colab import drive
drive.mount('/content/drive')

!cp '/content/drive/MyDrive/my project/kaggle.json' '/content'   #renew json file

import zipfile
import os

os.environ['KAGGLE_CONFIG_DIR'] = "/content"

"""Downloading dataset from kaggle"""

!kaggle datasets download -d deewakarchakraborty/portrait-paintings

zip_ref = zipfile.ZipFile('portrait-paintings.zip', 'r') #Opens the zip file in read mode
zip_ref.extractall('/content') #Extracts the files into the /content folder
zip_ref.close()

"""
Deep Convolutional GAN (DCGAN)

We'll be using DCGAN for this task."""

import torch
from torch import nn
from tqdm.auto import tqdm
from torchvision import transforms
from torchvision.datasets import MNIST
from torchvision.utils import make_grid
from torch.utils.data import DataLoader
import matplotlib.pyplot as plt



def show_tensor_images(image_tensor, num_images=20, size=(1, 128, 128)):
    '''
    Function for visualizing images: Given a tensor of images, number of images, and
    size per image, plots and prints the images in an uniform grid.
    '''
    image_tensor = (image_tensor + 1) / 2
    image_unflat = image_tensor.detach().cpu()
    image_grid = make_grid(image_unflat[:num_images], nrow=5)
    plt.imshow(image_grid.permute(1, 2, 0).squeeze())
    plt.show()

"""**Generator**
The first component we'll make is the generator. We'll be using 5 layers in this.
"""

class Generator(nn.Module):
    '''
    Generator Class
    Values:
        z_dim: the dimension of the noise vector
        channels: the number of channels in the images
        hidden_dim: the inner dimension, a scalar
    '''
    def __init__(self, z_dim=256, channels=3, hidden_dim=64):
        super(Generator, self).__init__()
        self.z_dim = z_dim
        # Build the neural network
        self.gen = nn.Sequential(
            self.make_gen_block(z_dim, hidden_dim * 16),
            self.make_gen_block(hidden_dim * 16, hidden_dim * 8, kernel_size=2, stride=2),
            self.make_gen_block(hidden_dim * 8, hidden_dim * 8, kernel_size=2, stride=2),
            self.make_gen_block(hidden_dim * 8, hidden_dim * 4, kernel_size=2, stride=2),
            self.make_gen_block(hidden_dim * 4, hidden_dim * 4, kernel_size=2, stride=2),
            self.make_gen_block(hidden_dim * 4, channels, kernel_size=2, stride=2, final_layer=True),
        )

    def make_gen_block(self, input_channels, output_channels, kernel_size=4, stride=1, final_layer=False,padding = 'same'):
        '''
        Function to return a sequence of operations corresponding to a generator block of DCGAN,
        corresponding to a transposed convolution, a batchnorm (except for in the last layer), and an activation.
        Parameters:
            input_channels: how many channels the input feature representation has
            output_channels: how many channels the output feature representation should have
            kernel_size: the size of each convolutional filter, equivalent to (kernel_size, kernel_size)
            stride: the stride of the convolution
            final_layer: a boolean, true if it is the final layer and false otherwise
                      (affects activation and batchnorm)
        '''

        # Build the neural block
        if not final_layer:
            return nn.Sequential(  #we'll get 3 nn layers out of this
                torch.nn.ConvTranspose2d(input_channels, output_channels, kernel_size,stride),#ConvTranspose2d is used for upsampling or transposed convolution. It inflates the input tensor's spatial dimensions by applying a learnable upsampling operation.
                torch.nn.BatchNorm2d(output_channels),
                torch.nn.ReLU()
            )
        else: # Final Layer
            return nn.Sequential(
                torch.nn.ConvTranspose2d(input_channels, output_channels, kernel_size,stride),
                torch.nn.Tanh()
            )

    def unsqueeze_noise(self, noise):
        '''
        Function for completing a forward pass of the generator: Given a noise tensor,
        returns a copy of that noise with width and height = 1 and channels = z_dim.
        Parameters:
            noise: a noise tensor with dimensions (n_samples, z_dim)
        '''
        return noise.view(len(noise), self.z_dim, 1, 1)

    def forward(self, noise):
        '''
        Function for completing a forward pass of the generator: Given a noise tensor,
        returns generated images.
        Parameters:
            noise: a noise tensor with dimensions (n_samples, z_dim)
        '''
        x = self.unsqueeze_noise(noise)
        return self.gen(x)

def get_noise(n_samples, z_dim, device='cpu'):
    '''
    Function for creating noise vectors: Given the dimensions (n_samples, z_dim)
    creates a tensor of that shape filled with random numbers from the normal distribution.
    Parameters:
        n_samples: the number of samples to generate, a scalar
        z_dim: the dimension of the noise vector, a scalar
        device: the device type
    '''
    return torch.randn(n_samples, z_dim, device=device)

from torchsummary import summary
z_dim = 256     #noise vector that we take
device = "cuda" if torch.cuda.is_available() else "cpu"
device

# Instantiate Generator model
model = Generator()

# Move the model to the appropriate device (GPU/CPU)
model.to(device)

# Define the input shape (noise vector)
input_shape = (1, z_dim)  # Assuming z_dim is the dimension of the noise vector

# Generate a random noise sample to determine the input size for the summary
sample_noise = torch.randn(1, z_dim).to(device)

# Get the summary of the model
summary(model, input_shape)

"""**Discriminator**

The second component we need to create is the discriminator.

We will use 3 layers in our discriminator's neural network. Like with the generator, we'll need create the function to create a single neural network block for the discriminator.
"""

class Discriminator(nn.Module):
    '''
    Discriminator Class
    Values:
        channels: the number of channels in the images
        hidden_dim: the inner dimension
    '''
    def __init__(self, channels=3, hidden_dim=64):
        super(Discriminator, self).__init__()
        self.disc = nn.Sequential(
            self.make_disc_block(channels, hidden_dim),
            self.make_disc_block(hidden_dim, hidden_dim * 2,kernel_size =2 , stride = 2),
            self.make_disc_block(hidden_dim*2, hidden_dim *4),
            self.make_disc_block(hidden_dim*4, hidden_dim *8),
            self.make_disc_block(hidden_dim*8, hidden_dim *16),
            self.make_disc_block(hidden_dim * 16, 1, final_layer=True),
        )
    def make_disc_block(self, input_channels, output_channels, kernel_size=2, stride=2, final_layer=False):
        '''
        Function to return a sequence of operations corresponding to a discriminator block of DCGAN,
        corresponding to a convolution, a batchnorm (except for in the last layer), and an activation.
        Parameters:
            input_channels: how many channels the input feature representation has
            output_channels: how many channels the output feature representation should have
            kernel_size: the size of each convolutional filter, equivalent to (kernel_size, kernel_size)
            stride: the stride of the convolution
            final_layer: a boolean, true if it is the final layer and false otherwise
                      (affects activation and batchnorm)
        '''

        # Build the neural block
        if not final_layer:
            return nn.Sequential(
                torch.nn.Conv2d(input_channels, output_channels, kernel_size,stride),
                torch.nn.BatchNorm2d(output_channels),
                torch.nn.LeakyReLU(.2)
            )
        else: # Final Layer
            return nn.Sequential(
                torch.nn.Conv2d(input_channels, output_channels, kernel_size=4,stride=1),
            )

    def forward(self, image):
        '''
        Function for completing a forward pass of the discriminator: Given an image tensor,
        returns a 1-dimension tensor representing fake/real.
        Parameters:
            image: a flattened image tensor with dimension (im_dim)
        '''
        disc_pred = self.disc(image)
        return disc_pred.view(len(disc_pred), -1)


# Instantiate your Discriminator model
discriminator_model = Discriminator()

# Move the model to the appropriate device (GPU/CPU)
discriminator_model.to(device)

# Assuming input shape for our discriminator
input_shape = (3, 128, 128)  #  RGB images of size 64x64

# Get the summary of the model
summary(discriminator_model, input_shape)

"""**Tranining Step**"""

from PIL import Image
import torchvision.transforms as transforms
from torch.utils.data import Dataset, DataLoader

criterion = nn.BCEWithLogitsLoss()  #loss function

display_step = 225        #how often we display our output
batch_size = 128          #number of images per forward/backward pass
lr = 0.0002               #learning rate

# These parameters control the optimizer's momentum:
beta_1 = 0.5
beta_2 = 0.999

#transformation of input images
transform = transforms.Compose([
    transforms.Resize((128, 128)),
    transforms.ToTensor(),  # Convert image to tensor
    transforms.Normalize((0.5,), (0.5,))  #dataset is then normalized to a range [-1,1]
])

"""Getting our data and creating dataloader:"""

class Dataset(Dataset):
    def __init__(self, root_dir, transform=None):
        self.root_dir = root_dir
        self.transform = transform
        self.image_list = os.listdir(root_dir)  # Get list of image filenames

    def __len__(self):
        return len(self.image_list)

    def __getitem__(self, idx):
        img_name = os.path.join(self.root_dir, self.image_list[idx])
        image = Image.open(img_name).convert('RGB')  # Open image in RGB mode

        if self.transform:
            image = self.transform(image)

        label = 1  # Replace this with label extraction logic

        return image, label

# Directory containing your input data images
dataset_path = '/content/Images'

# Initialize the custom dataset
dataset = Dataset(root_dir=dataset_path, transform=transform)

# Create DataLoader

dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

gen = Generator(z_dim).to(device)
gen_opt = torch.optim.Adam(gen.parameters(), lr=lr, betas=(beta_1, beta_2))
disc = Discriminator().to(device)
disc_opt = torch.optim.Adam(disc.parameters(), lr=lr, betas=(beta_1, beta_2))

# we can initialize the weights to the normal distribution
# with mean 0 and standard deviation 0.02....usually done with gans
def weights_init(m):
    if isinstance(m, nn.Conv2d) or isinstance(m, nn.ConvTranspose2d):
        torch.nn.init.normal_(m.weight, 0.0, 0.02)
    if isinstance(m, nn.BatchNorm2d):
        torch.nn.init.normal_(m.weight, 0.0, 0.02)
        torch.nn.init.constant_(m.bias, 0)
gen = gen.apply(weights_init)
disc = disc.apply(weights_init)

"""Finally, we can train our GAN! For each epoch, we will process the entire dataset in batches. For every batch, we will update the discriminator and generator. Then, we can see DCGAN's results!"""

n_epochs = 150
cur_step = 0
mean_generator_loss = 0
mean_discriminator_loss = 0
for epoch in range(n_epochs):
    # Dataloader returns the batches
    for real, _ in tqdm(dataloader):
        cur_batch_size = len(real)
        real = real.to(device)

        ## Update discriminator ##
        disc_opt.zero_grad()
        fake_noise = get_noise(cur_batch_size, z_dim, device=device)
        fake = gen(fake_noise)
        disc_fake_pred = disc(fake.detach())
        disc_fake_loss = criterion(disc_fake_pred, torch.zeros_like(disc_fake_pred))
        disc_real_pred = disc(real)
        disc_real_loss = criterion(disc_real_pred, torch.ones_like(disc_real_pred))
        disc_loss = (disc_fake_loss + disc_real_loss) / 2

        # Keep track of the average discriminator loss
        mean_discriminator_loss += disc_loss.item() / display_step
        # Update gradients
        disc_loss.backward(retain_graph=True)
        # Update optimizer
        disc_opt.step()

        ## Update generator ##
        gen_opt.zero_grad()
        fake_noise_2 = get_noise(cur_batch_size, z_dim, device=device)
        fake_2 = gen(fake_noise_2)
        disc_fake_pred = disc(fake_2)
        gen_loss = criterion(disc_fake_pred, torch.ones_like(disc_fake_pred))
        gen_loss.backward()
        gen_opt.step()

        # Keep track of the average generator loss
        mean_generator_loss += gen_loss.item() / display_step

        ## Visualization code ##
        if cur_step % display_step == 0 and cur_step > 0:
            print(f"Epoch {epoch}, step {cur_step}: Generator loss: {mean_generator_loss}, discriminator loss: {mean_discriminator_loss}")
            show_tensor_images(fake)
            show_tensor_images(real)
            mean_generator_loss = 0
            mean_discriminator_loss = 0
        cur_step += 1
