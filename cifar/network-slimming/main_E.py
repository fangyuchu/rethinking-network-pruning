from __future__ import print_function
import os
import argparse
import shutil
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torchvision import datasets, transforms
from torch.autograd import Variable
from datetime import datetime
import models
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

# Training settings
parser = argparse.ArgumentParser(description='PyTorch Slimming CIFAR training')
parser.add_argument('--dataset', type=str, default='cifar100',
                    help='training dataset (default: cifar100)')
parser.add_argument('--sparsity-regularization', '-sr', dest='sr', action='store_true',
                    help='train with channel sparsity regularization')
parser.add_argument('--s', type=float, default=0.0001,
                    help='scale sparse rate (default: 0.0001)')
parser.add_argument('--batch-size', type=int, default=128, metavar='N',
                    help='input batch size for training (default: 64)')
parser.add_argument('--test-batch-size', type=int, default=128, metavar='N',
                    help='input batch size for testing (default: 256)')
parser.add_argument('--epochs', type=int, default=160, metavar='N',
                    help='number of epochs to train (default: 160)')
parser.add_argument('--start-epoch', default=0, type=int, metavar='N',
                    help='manual epoch number (useful on restarts)')
parser.add_argument('--lr', type=float, default=0.1, metavar='LR',
                    help='learning rate (default: 0.1)')
parser.add_argument('--momentum', type=float, default=0.9, metavar='M',
                    help='SGD momentum (default: 0.9)')
parser.add_argument('--weight-decay', '--wd', default=1e-4, type=float,
                    metavar='W', help='weight decay (default: 1e-4)')
parser.add_argument('--resume', default='', type=str, metavar='PATH',
                    help='path to latest checkpoint (default: none)')
parser.add_argument('--no-cuda', action='store_true', default=False,
                    help='disables CUDA training')
parser.add_argument('--seed', type=int, default=1, metavar='S',
                    help='random seed (default: 1)')
parser.add_argument('--log-interval', type=int, default=100, metavar='N',
                    help='how many batches to wait before logging training status')
parser.add_argument('--save', default='./logs', type=str, metavar='PATH',
                    help='path to save prune model (default: current directory)')
parser.add_argument('--arch', default='resnet', type=str,
                    help='architecture to use')
parser.add_argument('--scratch',default='', type=str,
                    help='the PATH to the pruned model')
parser.add_argument('--depth', default=164, type=int,
                    help='depth of the neural network')

args = parser.parse_args()
args.cuda = not args.no_cuda and torch.cuda.is_available()
args.arch='resnet'
#cifar10
# base_path='/home/swim/fang/rethinking-network-pruning/cifar/network-slimming/data/model_saved/resnet_1601'
# base_path='/home/victorfang/rethinking-network-pruning/cifar/network-slimming/data/model_saved/resnet_3113'
# base_path='/home/victorfang/rethinking-network-pruning/cifar/network-slimming/data/model_saved/resnet_6427'
# base_path='/home/victorfang/rethinking-network-pruning/cifar/network-slimming/data/model_saved/resnet_1601'
# base_path='/home/victorfang/rethinking-network-pruning/cifar/network-slimming/data/model_saved/vgg_6871'
# base_path='/home/victorfang/rethinking-network-pruning/cifar/network-slimming/data/model_saved/vgg_8578'
# base_path='/home/victorfang/rethinking-network-pruning/cifar/network-slimming/data/model_saved/vgg_9476'
#cifar100
base_path='/home/victorfang/PycharmProjects/rethinking-network-pruning/cifar/network-slimming/data/model_saved/resnet56_9326'
# base_path='/home/victorfang/PycharmProjects/rethinking-network-pruning/cifar/network-slimming/data/model_saved/resnet56_9393'
if args.arch == 'resnet':
    args.depth=164
elif args.arch == 'vgg':
    args.depth=19
prune_rate_list=[0.75,0.8,0.83,0.85,0.87,0.9,0.93,0.5,0.6,0.65,0.95,0.98]
# prune_rate_list=[0.75,0.8,0.83,0.85,0.87,0.4,0.5,0.6]

print(base_path)
for prune_ratio in prune_rate_list:
    print('current prune_ratio is:',prune_ratio)
    args.save=os.path.join(base_path,str(int(prune_ratio*100)))
    args.scratch=os.path.join(base_path,str(int(prune_ratio*100))+ 'pruned.pth.tar')

    torch.manual_seed(args.seed)
    if args.cuda:
        torch.cuda.manual_seed(args.seed)

    if not os.path.exists(args.save):
        os.makedirs(args.save)

    kwargs = {'num_workers': 2, 'pin_memory': True} if args.cuda else {}
    if args.dataset == 'cifar10':
        train_loader = torch.utils.data.DataLoader(
            datasets.CIFAR10('./data/dataset/cifar10', train=True, download=True,
                           transform=transforms.Compose([
                               transforms.Pad(4),
                               transforms.RandomCrop(32),
                               transforms.RandomHorizontalFlip(),
                               transforms.ToTensor(),
                               transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010))
                           ])),
            batch_size=args.batch_size, shuffle=True, **kwargs)
        test_loader = torch.utils.data.DataLoader(
            datasets.CIFAR10('./data/dataset/cifar10', train=False, transform=transforms.Compose([
                               transforms.ToTensor(),
                               transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010))
                           ])),
            batch_size=args.test_batch_size, shuffle=True, **kwargs)
    else:
        train_loader = torch.utils.data.DataLoader(
            datasets.CIFAR100('./data/dataset/cifar100', train=True, download=True,
                           transform=transforms.Compose([
                               transforms.Pad(4),
                               transforms.RandomCrop(32),
                               transforms.RandomHorizontalFlip(),
                               transforms.ToTensor(),
                               transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010))
                           ])),
            batch_size=args.batch_size, shuffle=True, **kwargs)
        test_loader = torch.utils.data.DataLoader(
            datasets.CIFAR100('./data/dataset/cifar100', train=False, transform=transforms.Compose([
                               transforms.ToTensor(),
                               transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010))
                           ])),
            batch_size=args.test_batch_size, shuffle=True, **kwargs)

    model = models.__dict__[args.arch](dataset=args.dataset, depth=args.depth)

    if args.scratch:
        checkpoint = torch.load(args.scratch)
        model = models.__dict__[args.arch](dataset=args.dataset, depth=args.depth, cfg=checkpoint['cfg'])
        model_ref = models.__dict__[args.arch](dataset=args.dataset, depth=args.depth, cfg=checkpoint['cfg'])
        model_ref.load_state_dict(checkpoint['state_dict'])
        print(checkpoint['cfg'])
        for m0, m1 in zip(model.modules(), model_ref.modules()):
            if isinstance(m0, models.channel_selection):
                m0.indexes.data = m1.indexes.data.clone()

    if args.cuda:
        model.cuda()

    optimizer = optim.SGD(model.parameters(), lr=args.lr, momentum=args.momentum, weight_decay=args.weight_decay)

    if args.resume:
        if os.path.isfile(args.resume):
            print("=> loading checkpoint '{}'".format(args.resume))
            checkpoint = torch.load(args.resume)
            args.start_epoch = checkpoint['epoch']
            best_prec1 = checkpoint['best_prec1']
            model.load_state_dict(checkpoint['state_dict'])
            optimizer.load_state_dict(checkpoint['optimizer'])
            print("=> loaded checkpoint '{}' (epoch {}) Prec1: {:f}"
                  .format(args.resume, checkpoint['epoch'], best_prec1))
        else:
            print("=> no checkpoint found at '{}'".format(args.resume))

    history_score = np.zeros((args.epochs - args.start_epoch + 1, 3))

    # additional subgradient descent on the sparsity-induced penalty term
    def updateBN():
        for m in model.modules():
            if isinstance(m, nn.BatchNorm2d):
                m.weight.grad.data.add_(args.s*torch.sign(m.weight.data))  # L1

    def train(epoch):
        model.train()
        global history_score
        avg_loss = 0.
        train_acc = 0.
        for batch_idx, (data, target) in enumerate(train_loader):
            if args.cuda:
                data, target = data.cuda(), target.cuda()
            # data, target = Variable(data), Variable(target)
            optimizer.zero_grad()
            output = model(data)
            loss = F.cross_entropy(output, target)
            avg_loss += loss.item()
            pred = output.data.max(1, keepdim=True)[1]
            train_acc += pred.eq(target.data.view_as(pred)).cpu().sum()
            loss.backward()
            if args.sr:
                updateBN()
            optimizer.step()
            if batch_idx % args.log_interval == 0:
                print('Train Epoch: {} [{}/{} ({:.1f}%)]\tLoss: {:.6f}'.format(
                    epoch, batch_idx * len(data), len(train_loader.dataset),
                    100. * batch_idx / len(train_loader), loss.item()))
        history_score[epoch][0] = avg_loss / len(train_loader)
        history_score[epoch][1] = train_acc / float(len(train_loader))

    def test():
        model.eval()
        test_loss = 0
        correct = 0
        for data, target in test_loader:
            if args.cuda:
                data, target = data.cuda(), target.cuda()
            data, target = Variable(data, volatile=True), Variable(target)
            output = model(data)
            test_loss += F.cross_entropy(output, target, size_average=False).item() # sum up batch loss
            pred = output.data.max(1, keepdim=True)[1] # get the index of the max log-probability
            correct += pred.eq(target.data.view_as(pred)).cpu().sum()

        test_loss /= len(test_loader.dataset)
        print('\n{} Test set: Average loss: {:.4f}, Accuracy: {}/{} ({:.1f}%)\n'.format(datetime.now(),
            test_loss, correct, len(test_loader.dataset),
            100. * correct / len(test_loader.dataset)))
        return correct / float(len(test_loader.dataset))

    def save_checkpoint(state, is_best, filepath,acc):
        torch.save(state, os.path.join(filepath, 'checkpoint.pth.tar'))
        if is_best:
            shutil.copyfile(os.path.join(filepath, 'checkpoint.pth.tar'), os.path.join(filepath, str(acc)+'model_best.pth.tar'))

    best_prec1 = 0.
    for epoch in range(args.start_epoch, args.epochs):
        if epoch in [args.epochs*0.5, args.epochs*0.75]:
            for param_group in optimizer.param_groups:
                param_group['lr'] *= 0.1
        train(epoch)
        prec1 = test()
        history_score[epoch][2] = prec1
        np.savetxt(os.path.join(args.save, 'record.txt'), history_score, fmt = '%10.5f', delimiter=',')
        is_best = prec1 > best_prec1
        best_prec1 = max(prec1, best_prec1)
        save_checkpoint({
            'epoch': epoch + 1,
            'state_dict': model.state_dict(),
            'best_prec1': best_prec1,
            'optimizer': optimizer.state_dict(),
        }, is_best, filepath=args.save,acc=prec1)

    print("Best accuracy: "+str(best_prec1))
    history_score[-1][0] = best_prec1
    np.savetxt(os.path.join(args.save, 'record.txt'), history_score, fmt = '%10.5f', delimiter=',')
