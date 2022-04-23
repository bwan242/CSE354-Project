'''
author: Sounak Mondal
'''

# std lib imports
from typing import Dict
from matplotlib.pyplot import axis
from pkg_resources import add_activation_listener

# external libs
import torch
import torch.nn as nn
import torch.nn.functional as F

torch.manual_seed(1337)

class SequenceToVector(nn.Module):
    """
    It is an abstract class defining SequenceToVector enocoder
    abstraction. To build you own SequenceToVector encoder, subclass
    this.

    Parameters
    ----------
    input_dim : ``str``
        Last dimension of the input input vector sequence that
        this SentenceToVector encoder will encounter.
    """
    def __init__(self,
                 input_dim: int) -> 'SequenceToVector':
        super(SequenceToVector, self).__init__()
        self._input_dim = input_dim

    def forward(self,
             vector_sequence: torch.Tensor,
             sequence_mask: torch.Tensor,
             training=False) -> Dict[str, torch.Tensor]:
        """
        Forward pass of Main Classifier.

        Parameters
        ----------
        vector_sequence : ``torch.Tensor``
            Sequence of embedded vectors of shape (batch_size, max_tokens_num, embedding_dim)
        sequence_mask : ``torch.Tensor``
            Boolean tensor of shape (batch_size, max_tokens_num). Entries with 1 indicate that
            token is a real token, and 0 indicate that it's a padding token.
        training : ``bool``
            Whether this call is in training mode or prediction mode.
            This flag is useful while applying dropout because dropout should
            only be applied during training.

        Returns
        -------
        An output dictionary consisting of:
        combined_vector : torch.Tensor
            A tensor of shape ``(batch_size, embedding_dim)`` representing vector
            compressed from sequence of vectors.
        layer_representations : torch.Tensor
            A tensor of shape ``(batch_size, num_layers, embedding_dim)``.
            For each layer, you typically have (batch_size, embedding_dim) combined
            vectors. This is a stack of them.
        """
        # ...
        # return {"combined_vector": combined_vector,
        #         "layer_representations": layer_representations}
        raise NotImplementedError


class DanSequenceToVector(SequenceToVector):
    """
    It is a class defining Deep Averaging Network based Sequence to Vector
    encoder. You have to implement this.

    Parameters
    ----------
    input_dim : ``str``
        Last dimension of the input input vector sequence that
        this SentenceToVector encoder will encounter.
    num_layers : ``int``
        Number of layers in this DAN encoder.
    dropout : `float`
        Token dropout probability as described in the paper.
    """
    def __init__(self, input_dim: int, num_layers: int, dropout: float = 0.2, device = 'cpu'):
        super(DanSequenceToVector, self).__init__(input_dim)
        # TODO(students): start

        # subclass of SequenceToVector
        self.num_layers = num_layers

        # likelihood of a word being dropped
        self.dropout = dropout 

        self.device = device

        self.layers = nn.Sequential()

        for i in range(num_layers):
                self.layers.add_module(f"linear{i+1}", nn.Linear(in_features=self._input_dim, out_features=self._input_dim))

                if i < num_layers - 1:
                    self.layers.add_module(f"RELU_{i+1}", nn.ReLU())

        # TODO(students): end

    def forward(self,
             vector_sequence: torch.Tensor,
             sequence_mask: torch.Tensor,
             training=False) -> torch.Tensor:
        # TODO(students): start

        # Unpack the dimensions vector_sequence into into variables
        # vector_sequence.shape is a tuple
        batch_size, max_tokens_num, _ = vector_sequence.shape

        # use this to get a list of number of words that are in each sequence
        total_words_in_sequences = torch.count_nonzero(sequence_mask, dim=1)

        # from paper: randomly drop some tokens before computing average to improve performance
        # don't do this if we're not training the model
        if training:

            # Randomly generate a dropout matrix to be applied as a mask
            dropout_matrix = self.gen_dropout_matrix(batch_size, max_tokens_num)

            # to help with applying mask to sequence
            # adding a third dimension of size 1 helps zero out the embedding vectors for
            # dropped tokens
            dropout_matrix = torch.unsqueeze(dropout_matrix, 2) 

            # element-wise multiplication
            vector_sequence = torch.mul(vector_sequence, dropout_matrix)

            # Get num of words (now less bc of dropped tokens)
            dropout_matrix = torch.squeeze(dropout_matrix) # reshape the dropout_matrix
            updated_seq_mask = torch.mul(sequence_mask, dropout_matrix)
            total_words_in_sequences = torch.count_nonzero(updated_seq_mask, dim=1)


        # Get average vector
        # Sum up the embeddings 
        vec_sum = torch.sum(vector_sequence, dim=1)

        # reshape the list of num words in each sequence for division operation
        total_words_in_sequences = torch.unsqueeze(total_words_in_sequences, 1)

        # shape: (batch_size, embedding_dim)
        # list of averaged vectors for each sequence
        combined_vector = torch.divide(vec_sum, total_words_in_sequences)

        # the layers will be added to this
        layer_representations = []

        # RELU activation is being considered as its own layer
        for fflayer in self.layers:
            combined_vector = fflayer(combined_vector)

            # add the representations after before undergoing relu activation
            if type(fflayer) == nn.modules.linear.Linear:
                layer_representations.append(combined_vector)
        

        # stack the representations and turn into a tensor
        layer_representations = torch.stack(layer_representations, dim=0)

        
        # TODO(students): end
        return {"combined_vector": combined_vector,
                "layer_representations": layer_representations}

        
    def gen_dropout_matrix(self, batch_size, max_tokens_num):
        """
        Helper function. Generate a matrix of shape batch_size by max_tokens_num
        Each of the values will range between the dropout probability and 1
        """

        dropout_matrix = torch.rand(batch_size, max_tokens_num)

        # Iterate through every entry
        for i, row in enumerate(dropout_matrix):

            for j, entry in enumerate(row):
                # If the number is <= dropout probabilty, token will be dropped
                # had to acces
                if entry <= self.dropout:
                    dropout_matrix[i][j] = torch.tensor(0, dtype=torch.float32)

                else:
                    dropout_matrix[i][j] = torch.tensor(1, dtype=torch.float32)


        return dropout_matrix
        

class GruSequenceToVector(SequenceToVector):
    """
    It is a class defining GRU based Sequence To Vector encoder.
    You have to implement this.

    Parameters
    ----------
    input_dim : ``str``
        Last dimension of the input input vector sequence that
        this SentenceToVector encoder will encounter.
    num_layers : ``int``
        Number of layers in this GRU-based encoder. Note that each layer
        is a GRU encoder unlike DAN where they were feedforward based.
    """
    def __init__(self, input_dim: int, num_layers: int, device = 'cpu'):
        super(GruSequenceToVector, self).__init__(input_dim)
        # TODO(students): start
        self.num_layers = num_layers

        self.gru = nn.GRU(input_size=self._input_dim, hidden_size=input_dim, num_layers=self.num_layers)

        # TODO(students): end

    def forward(self,
             vector_sequence: torch.Tensor,
             sequence_mask: torch.Tensor,
             training=False) -> torch.Tensor:
        # TODO(students): start

        # vector_sequence: batch_size * max_tokens_num * embedding_dimension (64, 209, 50)
        # sequence_mask: batch_size * max_tokens_num (64, 209) 

        # vector of the lengths of each review
        lengths = torch.count_nonzero(sequence_mask, dim=1)

        # method signature: (input, lengths, batch_first, enforce_sorted
        # batch_first defaults to False, but vector_sequence's first dim is batch size
        # enforce_sorted is false bc the sequences are not sorted by length
        vector_sequence = torch.nn.utils.rnn.pack_padded_sequence(vector_sequence, lengths=lengths, 
                                                                    batch_first=True, enforce_sorted=False)

        # as per pytorch docs:
        # output has shape (sequence_length, batch, num_directions * hidden_size)
        # h_n is a tensor with the repns at each later. Shape: (num_layers, batch_size, embedding_dim)
        output, h_n = self.gru(vector_sequence)

        layer_representations = h_n
        combined_vector =  layer_representations[-1, :, :] # the representation at the final layer
        
        
        # TODO(students): end
        return {"combined_vector": combined_vector,
                "layer_representations": layer_representations}
