'''
author: Sounak Mondal
'''
# external libs
import torch
import torch.nn as nn

# project imports
from util import load_pretrained_model

torch.manual_seed(1337)

class ProbingClassifier(nn.Module):
    def __init__(self,
                 pretrained_model_path: str,
                 layer_num: int,
                 input_dim: int,
                 classes_num: int,
                 device:str = 'cpu') -> 'ProbingClassifier':
        """
        It loads a pretrained main model. On the given input,
        it takes the representations it generates on certain layer
        and learns a linear classifier on top of these frozen
        features.

        Parameters
        ----------
        pretrained_model_path : ``str``
            Serialization directory of the main model which you
            want to probe at one of the layers.
        layer_num : ``int``
            Layer number of the pretrained model on which to learn
            a linear classifier probe.
        classes_num : ``int``
            Number of classes that the ProbingClassifier chooses from.
        """
        super(ProbingClassifier, self).__init__()
        self.device = device
        self._pretrained_model = load_pretrained_model(pretrained_model_path, device = device).to(device)
        for param in self._pretrained_model.parameters():
            param.requires_grad = False
        self._layer_num = layer_num
        self.device = device

        # TODO(students): start
        self.classes_num = classes_num
        self.input_dim = input_dim

        self.linear = nn.Linear(in_features=self.input_dim, out_features=self.classes_num)
        
        # TODO(students): end

    def forward(self, inputs: torch.Tensor, training: bool = False) -> torch.Tensor:
        inputs = inputs.to(self.device)
        """
        Forward pass of Probing Classifier.

        Parameters
        ----------
        inputs : ``torch.Tensor``
            Tensorized version of the batched input text. It is of shape:
            (batch_size, max_tokens_num) and entries are indices of tokens
            in to the vocabulary. 0 means that it's a padding token. max_tokens_num
            is maximum number of tokens in any text sequence in this batch.
        training : ``bool``
            Whether this call is in training mode or prediction mode.
            This flag is useful while applying dropout because dropout should
            only be applied during training.
        """
        # TODO(students): start

        # due to how the model was defined, training will be set to true
        # pass training as false to avoid dropout
        # This is the result of the model running on this text
        model_result = self._pretrained_model(inputs, training=False)

        # model_result is a dictionary
        layer_representations = model_result['layer_representations']

        # layer representations will be of shape [batch_size, layer_num, embedding_dim]
        frozen_layer_rep = layer_representations[:,self._layer_num-1,:]
        

        logits = self.linear(frozen_layer_rep)
        
        
        # TODO(students): end
        return {"logits": logits}
