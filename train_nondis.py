# Main training script - trains distributedly accordi
import os
import hydra

import torch
import torch.distributed as dist
import torch.multiprocessing as mp

from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig, OmegaConf
from tqdm import tqdm 

# Custom imports 
from datasets.dataloader import get_dataloaders
from learner.initialize_learner import init_learner
from datasets import *
from utils import *

class Workspace:
    def __init__(self, cfg : DictConfig) -> None:
        print(f'Workspace config: {OmegaConf.to_yaml(cfg)}')

        # Initialize hydra
        self.hydra_dir = HydraConfig.get().run.dir

        # Create the checkpoint directory - it will be inside the hydra directory
        cfg.checkpoint_dir = os.path.join(self.hydra_dir, 'saved_models')
        os.makedirs(cfg.checkpoint_dir, exist_ok=True) # Doesn't give an error if dir exists when exist_ok is set to True 
        
        # Set device and config
        self.cfg = cfg

    def train(self) -> None:
        device = torch.device('cuda')

        # It looks at the datatype type and returns the train and test loader accordingly
        train_loader, test_loader, _ = get_dataloaders(self.cfg)
        print("--------------------------------------------------finish loading!!!")

        # Initialize the learner - looks at the type of the agent to be initialized first
        learner = init_learner(self.cfg, device)

        best_loss = torch.inf 


        pbar = tqdm(total=self.cfg.train_epochs)
        # Initialize logger (wandb)
        if self.cfg.logger:
            wandb_exp_name = '-'.join(self.hydra_dir.split('/')[-2:])
            self.logger = Logger(self.cfg, wandb_exp_name, out_dir=self.hydra_dir)

        # Start the training
        for epoch in range(self.cfg.train_epochs):

            # Train the models for one epoch
            # train_loss, loss_dict = learner.train_epoch(train_loader)
            train_loss = learner.train_epoch(train_loader)

            pbar.set_description(f'Epoch {epoch}, Train loss: {train_loss:.5f}, Best loss: {best_loss:.5f}')
            pbar.update(1) # Update for each batch

            # Logging
            if self.cfg.logger and epoch % self.cfg.log_frequency == 0:
                self.logger.log({'epoch': epoch,
                                 'train loss': train_loss})
                # self.logger.log({"train/{}".format(x): y for (x, y) in loss_dict.items()})

            # Testing and saving the model
            if epoch % self.cfg.save_frequency == 0: # NOTE: Not sure why this is a problem but this could be the fix
                learner.save(self.cfg.checkpoint_dir, model_type='latest') # Always save the latest encoder
                # Test for one epoch
                if not self.cfg.self_supervised:
                    test_loss, test_loss_dict = learner.test_epoch(test_loader)
                else:
                    test_loss = train_loss # In BYOL (for ex) test loss is not important

                # Get the best loss
                if test_loss < best_loss:
                    best_loss = test_loss
                    learner.save(self.cfg.checkpoint_dir, model_type='best')

                # Logging
                pbar.set_description(f'Epoch {epoch}, Test loss: {test_loss:.5f}')
                if self.cfg.logger:
                    self.logger.log({'epoch': epoch,
                                    'test loss': test_loss})
                    self.logger.log({'epoch': epoch,
                                    'best loss': best_loss})


        pbar.close()

@hydra.main(version_base=None,config_path='configs', config_name = 'train')
def main(cfg : DictConfig) -> None:
    # We are only training everything distributedly
    assert cfg.distributed is False, "Use script only to train non-distributed"
    workspace = Workspace(cfg)
    workspace.train()
    
if __name__ == '__main__':
    main()