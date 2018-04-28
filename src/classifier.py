import torch
from torch import nn
from torch.autograd import Variable
from torchvision import models, datasets
from torchvision.transforms import transforms


class Classifier:

    def __init__(self, learning_rate, batch_size, train_dir, test_dir):
        self.train_metrics = []
        self.test_metrics = []

        # Create the model
        self.model = models.vgg16(pretrained=True)

        # Freeze the first few layers
        ct = 0
        for name, child in self.model.named_children():
            ct += 1
            if ct < 1:
                j = 0
                for name2, params in child.named_parameters():
                    j += 1
                    if j < 7:
                        params.requires_grad = False

        # Define a criterion for the loss function
        self.criterion = nn.CrossEntropyLoss()

        # Change the last layer of the model
        numb = self.model.classifier[6].in_features
        features = list(self.model.classifier.children())[:-1]
        features.extend([nn.Linear(numb, 20)])
        self.model.classifier = nn.Sequential(*features)

        # Define an optimizer for the loss function
        self.optimizer = torch.optim.SGD(
            self.model.classifier._modules['6'].parameters(),
            learning_rate
        )

        # Load the dataset images
        self.train_loader, self.test_loader = self.__load_the_data(train_dir, test_dir, batch_size)

    #
    #
    #
    @staticmethod
    def __load_the_data(train_dir, test_dir, batch_size):
        # Set normalization metrics for the data loaders
        normalize = transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )

        # Load the train directory and shuffle the images
        train_loader = torch.utils.data.DataLoader(
            datasets.ImageFolder(
                train_dir,
                transforms.Compose([
                    transforms.RandomResizedCrop(224),
                    transforms.RandomHorizontalFlip(),
                    transforms.ToTensor(),
                    normalize,
                ])
            ),
            batch_size=batch_size,
            shuffle=True,
        )

        # Load the test directory
        test_loader = torch.utils.data.DataLoader(
            datasets.ImageFolder(
                test_dir,
                transforms.Compose([
                    transforms.Resize(256),
                    transforms.CenterCrop(224),
                    transforms.ToTensor(),
                    normalize,
                ])
            ),
            batch_size=batch_size,
        )

        return train_loader, test_loader

    #
    #
    #
    def train(self):
        losses = AverageMeter()

        # switch to train mode
        self.model.train()

        for i, (inputs, labels) in enumerate(self.train_loader):
            inputs, labels = Variable(inputs), Variable(labels)

            # compute output
            output = self.model(inputs)
            loss = self.criterion(output, labels)

            # Record loss
            losses.update(loss.data[0], inputs.size(0))

            # compute gradient and do SGD step
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()

            # Store the metrics for plotting
            self.train_metrics.append({
                'loss': losses.val,
                'loss_avg': losses.avg
            })

            print('Batch: {0}/{1} --- Loss: {2} - Avg: {3}\n'.format(
                i + 1,
                len(self.train_loader),
                losses.val,
                losses.avg,
            ))

    #
    #
    #
    def test(self):
        losses = AverageMeter()
        top1 = AverageMeter()
        top5 = AverageMeter()

        # switch to evaluate mode
        self.model.eval()

        for i, (input, target) in enumerate(self.test_loader):
            # compute output
            input_variable, target_variable = Variable(input), Variable(target)

            outputs = self.model(input_variable)
            loss = self.criterion(outputs, target_variable)

            # measure accuracy and record loss
            prec1, prec5 = self.__accuracy(outputs.data, target_variable.data, topk=(1, 5))
            losses.update(loss.data[0], input_variable.size(0))
            top1.update(prec1[0], input_variable.size(0))
            top5.update(prec5[0], input_variable.size(0))

            # Store the metrics for plotting
            self.test_metrics.append({
                'top1': top1.val,
                'top1_avg': top1.avg,
                'top5': top5.val,
                'top5_avg': top5.avg
            })

            # Print the metrics for info
            print('Batch: {0}/{1} --- Top1: {2} - Avg: {3} --- Top5: {4} - Avg: {5}\n'.format(
                    i + 1,
                    len(self.test_loader),
                    float(top1.val),
                    float(top1.avg),
                    float(top5.val),
                    float(top5.avg)
                )
            )

    #
    #
    #
    def plot_the_results(self):
        pass

    #
    #
    #
    @staticmethod
    def __accuracy(outputs, labels, topk):
        """Computes the precision@k for the specified values of k"""
        maxk = max(topk)
        batch_size = labels.size(0)

        _, pred = outputs.topk(maxk, 1, True, True)
        pred = pred.t()
        correct = pred.eq(labels.view(1, -1).expand_as(pred))

        res = []
        for k in topk:
            correct_k = correct[:k].view(-1).float().sum(0, keepdim=True)
            res.append(correct_k.mul_(100.0 / batch_size))

        return res


class AverageMeter:
    """Computes and stores the average and current value"""

    def __init__(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count