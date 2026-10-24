from torch import nn
from torchvision.models import (
    resnet18,
    ResNet18_Weights,
    efficientnet_b0,
    EfficientNet_B0_Weights,
    convnext_tiny,
    ConvNeXt_Tiny_Weights,
)


class Detector(nn.Module):
    def __init__(self, modality, architecture="resnet18", pretrained=True):
        super().__init__()
        if modality == "audio":
            self.encoder = nn.Sequential(
                nn.Conv2d(1, 32, 3, padding=1),
                nn.BatchNorm2d(32),
                nn.ReLU(),
                nn.MaxPool2d(2),
                nn.Conv2d(32, 64, 3, padding=1),
                nn.BatchNorm2d(64),
                nn.ReLU(),
                nn.MaxPool2d(2),
                nn.Conv2d(64, 128, 3, padding=1),
                nn.ReLU(),
                nn.AdaptiveAvgPool2d(1),
                nn.Flatten(),
            )
            dimension = 128
        elif architecture == "efficientnet_b0":
            base = efficientnet_b0(
                weights=EfficientNet_B0_Weights.DEFAULT if pretrained else None
            )
            dimension = base.classifier[1].in_features
            base.classifier = nn.Identity()
            self.encoder = base
        elif architecture == "convnext_tiny":
            base = convnext_tiny(weights=ConvNeXt_Tiny_Weights.DEFAULT if pretrained else None)
            dimension = base.classifier[2].in_features
            base.classifier[2] = nn.Identity()
            self.encoder = base
        elif architecture == "resnet18":
            base = resnet18(weights=ResNet18_Weights.DEFAULT if pretrained else None)
            dimension = base.fc.in_features
            base.fc = nn.Identity()
            self.encoder = base
        else:
            raise ValueError(f"Unsupported architecture: {architecture}")
        self.head = nn.Sequential(nn.Dropout(0.2), nn.Linear(dimension, 1))

    def forward(self, x):
        embedding = self.encoder(x)
        return self.head(embedding).squeeze(1), embedding
