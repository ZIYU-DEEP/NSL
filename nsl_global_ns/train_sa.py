import numpy as numpy
import tensorflow as tf
from loss import loss2
from cifar10_input import *
from spherenet import SphereNet
import os

# assign an available GPU
os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"]="0"

n_class = 10
batch_sz = 128
batch_test = 100
max_epoch = 64000
lr = 1e-3

# directory for training dataset
data_path = '../data/cifar-10/'
# directory to save models
model_file = 'models/'

is_training = tf.placeholder("bool")
tr_images, tr_labels = distorted_inputs(data_path, batch_sz)
te_images, te_labels = inputs(True, data_path, batch_test)

images, labels = tf.cond(is_training, lambda: [tr_images, tr_labels], lambda: [te_images, te_labels])

spherenet = SphereNet()
spherenet.build(images, n_class, is_training)

fit_loss = loss2(spherenet.score, labels, n_class, 'c_entropy') 
loss_op = fit_loss

reg_loss_list = tf.losses.get_regularization_losses()
if len(reg_loss_list) != 0:
    reg_loss = tf.add_n(reg_loss_list)
    loss_op += reg_loss

orth_loss_list = tf.get_collection('orth_constraint')
if len(orth_loss_list) != 0:
    orth_loss = tf.add_n(orth_loss_list)
    loss_op += orth_loss


lr_ = tf.placeholder("float")
update_op = tf.train.AdamOptimizer(lr_).minimize(loss_op)
acc_op = tf.reduce_mean(tf.to_float(tf.equal(labels, tf.to_int32(spherenet.pred))))

sess = tf.Session()
sess.run(tf.global_variables_initializer())
coord = tf.train.Coordinator()
threads = tf.train.start_queue_runners(sess=sess, coord=coord)

for i in xrange(max_epoch+1):

    if i==34000:
        lr = lr/10
    if i==54000:
        lr = lr/10

    if len(orth_loss_list) != 0:
        fit, reg, orth, acc, _ = sess.run([fit_loss, reg_loss, orth_loss, acc_op, update_op],
                                                {lr_: lr, is_training: True})
        if i % 100 == 0 and i != 0:
            print('====iteration_%d: fit=%.4f, reg=%.4f, orth=%.4f, acc=%.4f' 
                    % (i, fit, reg, orth, acc))
    else:
        fit, reg, acc, _ = sess.run([fit_loss, reg_loss, acc_op, update_op],
                                            {lr_: lr, is_training: True})

        if i % 100 == 0 and i != 0:
            print('====iteration_%d: fit=%.4f, reg=%.4f, acc=%.4f' 
                    % (i, fit, reg, acc))
    
    if i%500==0 and i!=0:
        n_test = 10000
        acc = 0.0
        for j in xrange(int(n_test/batch_test)):
            acc = acc + sess.run(acc_op, {is_training: False})
        acc = acc*batch_test/n_test
        print('++++iteration_%d: test acc=%.4f' % (i, acc))

    if i%16000==0 and i!=0:
        tf.train.Saver().save(sess, model_file+str(i))
