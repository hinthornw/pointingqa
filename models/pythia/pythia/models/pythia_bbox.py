# Copyright (c) Facebook, Inc. and its affiliates.
import torch

from pythia.common.registry import registry
from pythia.models.pythia import Pythia
from pythia.modules.layers import ClassifierLayer


@registry.register_model("pythia_globalbbox")
class Pythia_globalbbox(Pythia):
    def __init__(self, config):
        super().__init__(config)

    def build(self):
        self._init_feature_encoders("context")
        super().build()

    def get_optimizer_parameters(self, config):
        params = super().get_optimizer_parameters(config)
        params += [
            {
                "params": self.context_feature_encoders.parameters(),
                "lr": (config["optimizer_attributes"]["params"]["lr"] * 0.1),
            },
        ]

        return params

    def process_feature_encoding(
            self, attr, sample_list, text_embedding_total, extra=[], batch_size_t=None, context=None
    ):
        feature_embeddings = []
        feature_attentions = []
        features = []
        batch_size_t = (
            sample_list.get_batch_size() if batch_size_t is None else batch_size_t
        )

        # Convert list of keys to the actual values                                                                                       \
                                                                                                                                           
        extra = sample_list.get_fields(extra)

        feature_idx = 0

        # Get all of the features, which are in the form, "image_feature_0"                                                               \
                                                                                                                                           
        # "image_feature_1" ...                                                                                                           \
                                                                                                                                           
        while True:
            feature = getattr(
                sample_list, "{}_feature_{:d}".format(attr, feature_idx), None
            )
            if feature is None:
                break
            feature_idx += 1
            feature = feature[:batch_size_t]
            features.append(feature)
        
        feature_encoders = getattr(self, attr + "_feature_encoders")
        # Each feature should have a separate image feature encoders                                                                      \
                                                                                                                                           
        assert len(features) == len(feature_encoders), (
            "Number of feature encoders, {} are not equal "
            "to number of features, {}.".format(len(feature_encoders), len(features))
        )

        # encode the feature, no attention needed                                                                                          
        feature_encodings = []

         # Now, iterate to get final attended image features                                                                              \
                                                                                                                                           
        for i, feature in enumerate(features):
            # Get info related to the current feature. info is generally                                                                  \
                                                                                                                                           
            # in key of format "image_info_0" for 0th feature                                                                             \
                                                                                                                                           
            feature_info = getattr(sample_list, "{}_info_{:d}".format(attr, i), {})
            # For Pythia, we need max_features to mask attention                                                                          \
                                                                                                                                           
            feature_dim = getattr(feature_info, "max_features", None)
            if feature_dim is not None:
                feature_dim = feature_dim[:batch_size_t]

            encoders_attr = attr + "_feature_encoders"
            feature_encoder = getattr(self, encoders_attr)[i]

            # Encode the features                                                                                                         \
                                                                                                                                           
            encoded_feature = feature_encoder(feature)
            feature_encodings.append(encoded_feature)

        feature_encoding_total = torch.cat(feature_encodings, dim=1)
        return feature_encoding_total

    def forward(self, sample_list):
        sample_list.text = self.word_embedding(sample_list.text)
        text_embedding_total = self.process_text_embedding(sample_list)

        context_encoded = self.process_feature_encoding(
            "context", sample_list, text_embedding_total 
        )

        image_embedding_total, att_img = self.process_feature_embedding(
            "image", sample_list, text_embedding_total, context=context_encoded
        )

        joint_embedding = self.combine_embeddings(
            ["image", "text"],
            [image_embedding_total, text_embedding_total, context_encoded],
        )

        scores = self.calculate_logits(joint_embedding)
        return {"scores": scores, "att": att_img[0].squeeze()}
