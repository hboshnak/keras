# Copyright 2019 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Tests for image preprocessing layers."""

import functools
from absl.testing import parameterized

import keras
from keras.engine import sequential
from keras.layers.preprocessing import image_preprocessing
from keras.testing_infra import test_combinations
from keras.testing_infra import test_utils
import numpy as np
import tensorflow.compat.v2 as tf
# pylint: disable=g-direct-tensorflow-import
from tensorflow.python.ops import stateless_random_ops


@test_combinations.run_all_keras_modes(always_skip_v1=True)
class ResizingTest(test_combinations.TestCase):

  def _run_test(self, kwargs, expected_height, expected_width):
    np.random.seed(1337)
    num_samples = 2
    orig_height = 5
    orig_width = 8
    channels = 3
    kwargs.update({'height': expected_height, 'width': expected_width})
    with test_utils.use_gpu():
      test_utils.layer_test(
          image_preprocessing.Resizing,
          kwargs=kwargs,
          input_shape=(num_samples, orig_height, orig_width, channels),
          expected_output_shape=(None, expected_height, expected_width,
                                 channels))

  @parameterized.named_parameters(('down_sample_bilinear_2_by_2', {
      'interpolation': 'bilinear'
  }, 2, 2), ('down_sample_bilinear_3_by_2', {
      'interpolation': 'bilinear'
  }, 3, 2), ('down_sample_nearest_2_by_2', {
      'interpolation': 'nearest'
  }, 2, 2), ('down_sample_nearest_3_by_2', {
      'interpolation': 'nearest'
  }, 3, 2), ('down_sample_area_2_by_2', {
      'interpolation': 'area'
  }, 2, 2), ('down_sample_area_3_by_2', {
      'interpolation': 'area'
  }, 3, 2), ('down_sample_crop_to_aspect_ratio_3_by_2', {
      'interpolation': 'bilinear',
      'crop_to_aspect_ratio': True,
  }, 3, 2))
  def test_down_sampling(self, kwargs, expected_height, expected_width):
    self._run_test(kwargs, expected_height, expected_width)

  @parameterized.named_parameters(('up_sample_bilinear_10_by_12', {
      'interpolation': 'bilinear'
  }, 10, 12), ('up_sample_bilinear_12_by_12', {
      'interpolation': 'bilinear'
  }, 12, 12), ('up_sample_nearest_10_by_12', {
      'interpolation': 'nearest'
  }, 10, 12), ('up_sample_nearest_12_by_12', {
      'interpolation': 'nearest'
  }, 12, 12), ('up_sample_area_10_by_12', {
      'interpolation': 'area'
  }, 10, 12), ('up_sample_area_12_by_12', {
      'interpolation': 'area'
  }, 12, 12), ('up_sample_crop_to_aspect_ratio_12_by_14', {
      'interpolation': 'bilinear',
      'crop_to_aspect_ratio': True,
  }, 12, 14))
  def test_up_sampling(self, kwargs, expected_height, expected_width):
    self._run_test(kwargs, expected_height, expected_width)

  def test_down_sampling_numeric(self):
    for dtype in (np.int64, np.float32):
      with test_utils.use_gpu():
        input_image = np.reshape(np.arange(0, 16), (1, 4, 4, 1)).astype(dtype)
        layer = image_preprocessing.Resizing(
            height=2, width=2, interpolation='nearest')
        output_image = layer(input_image)
        # pyformat: disable
        expected_output = np.asarray([
            [5, 7],
            [13, 15]
        ]).astype(dtype)
        # pyformat: enable
        expected_output = np.reshape(expected_output, (1, 2, 2, 1))
        self.assertAllEqual(expected_output, output_image)

  def test_up_sampling_numeric(self):
    for dtype in (np.int64, np.float32):
      with test_utils.use_gpu():
        input_image = np.reshape(np.arange(0, 4), (1, 2, 2, 1)).astype(dtype)
        layer = image_preprocessing.Resizing(
            height=4, width=4, interpolation='nearest')
        output_image = layer(input_image)
        # pyformat: disable
        expected_output = np.asarray([
            [0, 0, 1, 1],
            [0, 0, 1, 1],
            [2, 2, 3, 3],
            [2, 2, 3, 3]
        ]).astype(dtype)
        # pyformat: enable
        expected_output = np.reshape(expected_output, (1, 4, 4, 1))
        self.assertAllEqual(expected_output, output_image)

  @parameterized.named_parameters(('reshape_bilinear_10_by_4', {
      'interpolation': 'bilinear'
  }, 10, 4))
  def test_reshaping(self, kwargs, expected_height, expected_width):
    self._run_test(kwargs, expected_height, expected_width)

  def test_invalid_interpolation(self):
    with self.assertRaises(NotImplementedError):
      image_preprocessing.Resizing(5, 5, 'invalid_interpolation')

  def test_config_with_custom_name(self):
    layer = image_preprocessing.Resizing(5, 5, name='image_preproc')
    config = layer.get_config()
    layer_1 = image_preprocessing.Resizing.from_config(config)
    self.assertEqual(layer_1.name, layer.name)

  def test_crop_to_aspect_ratio(self):
    with test_utils.use_gpu():
      input_image = np.reshape(np.arange(0, 16), (1, 4, 4, 1)).astype('float32')
      layer = image_preprocessing.Resizing(4, 2, crop_to_aspect_ratio=True)
      output_image = layer(input_image)
      expected_output = np.asarray([
          [1, 2],
          [5, 6],
          [9, 10],
          [13, 14],
      ]).astype('float32')
      expected_output = np.reshape(expected_output, (1, 4, 2, 1))
      self.assertAllEqual(expected_output, output_image)

  def test_unbatched_image(self):
    with test_utils.use_gpu():
      input_image = np.reshape(np.arange(0, 16), (4, 4, 1)).astype('float32')
      layer = image_preprocessing.Resizing(2, 2, interpolation='nearest')
      output_image = layer(input_image)
      expected_output = np.asarray([
          [5, 7],
          [13, 15],
      ]).astype('float32')
      expected_output = np.reshape(expected_output, (2, 2, 1))
      self.assertAllEqual(expected_output, output_image)

  @parameterized.named_parameters(('crop_to_aspect_ratio_false', False),
                                  ('crop_to_aspect_ratio_true', True))
  def test_ragged_image(self, crop_to_aspect_ratio):
    with test_utils.use_gpu():
      inputs = tf.ragged.constant([
          np.ones((8, 8, 1)),
          np.ones((8, 4, 1)),
          np.ones((4, 8, 1)),
          np.ones((2, 2, 1)),
      ], dtype='float32')
      layer = image_preprocessing.Resizing(
          2,
          2,
          interpolation='nearest',
          crop_to_aspect_ratio=crop_to_aspect_ratio)
      outputs = layer(inputs)
      expected_output = [[[[1.], [1.]], [[1.], [1.]]],
                         [[[1.], [1.]], [[1.], [1.]]],
                         [[[1.], [1.]], [[1.], [1.]]],
                         [[[1.], [1.]], [[1.], [1.]]]]
      self.assertIsInstance(outputs, tf.Tensor)
      self.assertNotIsInstance(outputs, tf.RaggedTensor)
      self.assertAllEqual(expected_output, outputs)

  @test_utils.run_v2_only
  def test_output_dtypes(self):
    inputs = np.array([[[1], [2]], [[3], [4]]], dtype='float64')
    layer = image_preprocessing.Resizing(2, 2)
    self.assertAllEqual(layer(inputs).dtype, 'float32')
    layer = image_preprocessing.Resizing(2, 2, dtype='uint8')
    self.assertAllEqual(layer(inputs).dtype, 'uint8')

  @parameterized.named_parameters(
      ('batch_crop_to_aspect_ratio', True, True),
      ('batch_dont_crop_to_aspect_ratio', False, True),
      ('single_sample_crop_to_aspect_ratio', True, False),
      ('single_sample_dont_crop_to_aspect_ratio', False, False),
  )
  def test_static_shape_inference(self, crop_to_aspect_ratio, batch):
    channels = 3
    input_height = 8
    input_width = 8
    target_height = 4
    target_width = 6
    layer = image_preprocessing.Resizing(
        target_height, target_width, crop_to_aspect_ratio=crop_to_aspect_ratio)
    unit_test = self

    @tf.function
    def tf_function(img):
      unit_test.assertListEqual([input_height, input_width, channels],
                                img.shape.as_list()[-3:])
      img = layer(img)
      unit_test.assertListEqual([target_height, target_width, channels],
                                img.shape.as_list()[-3:])
      return img

    with test_utils.use_gpu():
      if batch:
        input_shape = (2, input_height, input_width, channels)
      else:
        input_shape = (input_height, input_width, channels)
      img_data = np.random.random(size=input_shape).astype('float32')
      tf_function(img_data)


def get_numpy_center_crop(images, expected_height, expected_width):
  orig_height = images.shape[1]
  orig_width = images.shape[2]
  height_start = int((orig_height - expected_height) / 2)
  width_start = int((orig_width - expected_width) / 2)
  height_end = height_start + expected_height
  width_end = width_start + expected_width
  return images[:, height_start:height_end, width_start:width_end, :]


@test_combinations.run_all_keras_modes(always_skip_v1=True)
class CenterCropTest(test_combinations.TestCase):

  def _run_test(self, expected_height, expected_width):
    np.random.seed(1337)
    num_samples = 2
    orig_height = 5
    orig_width = 8
    channels = 3
    kwargs = {'height': expected_height, 'width': expected_width}
    input_images = np.random.random(
        (num_samples, orig_height, orig_width, channels)).astype(np.float32)
    expected_output = get_numpy_center_crop(input_images, expected_height,
                                            expected_width)
    with test_utils.use_gpu():
      test_utils.layer_test(
          image_preprocessing.CenterCrop,
          kwargs=kwargs,
          input_shape=(num_samples, orig_height, orig_width, channels),
          input_data=input_images,
          expected_output=expected_output,
          expected_output_shape=(None, expected_height, expected_width,
                                 channels))

  @parameterized.named_parameters(('center_crop_3_by_4', 3, 4),
                                  ('center_crop_3_by_2', 3, 2))
  def test_center_crop_aligned(self, expected_height, expected_width):
    self._run_test(expected_height, expected_width)

  @parameterized.named_parameters(('center_crop_4_by_5', 4, 5),
                                  ('center_crop_4_by_3', 4, 3))
  def test_center_crop_mis_aligned(self, expected_height, expected_width):
    self._run_test(expected_height, expected_width)

  @parameterized.named_parameters(('center_crop_4_by_6', 4, 6),
                                  ('center_crop_3_by_2', 3, 2))
  def test_center_crop_half_mis_aligned(self, expected_height, expected_width):
    self._run_test(expected_height, expected_width)

  def test_input_smaller_than_crop_box(self):
    np.random.seed(1337)
    height, width = 10, 8
    inp = np.random.random((12, 3, 3, 3))
    with test_utils.use_gpu():
      layer = image_preprocessing.CenterCrop(height, width)
      actual_output = layer(inp)
      # In this case, output should equal resizing with crop_to_aspect ratio.
      resize_layer = image_preprocessing.Resizing(
          height, width, crop_to_aspect_ratio=True)
      expected_output = resize_layer(inp)
      self.assertAllEqual(expected_output, actual_output)

  def test_config_with_custom_name(self):
    layer = image_preprocessing.CenterCrop(5, 5, name='image_preproc')
    config = layer.get_config()
    layer_1 = image_preprocessing.CenterCrop.from_config(config)
    self.assertEqual(layer_1.name, layer.name)

  def test_unbatched_image(self):
    with test_utils.use_gpu():
      input_image = np.reshape(np.arange(0, 16), (4, 4, 1)).astype('float32')
      layer = image_preprocessing.CenterCrop(2, 2)
      output_image = layer(input_image)
      expected_output = np.asarray([
          [5, 6],
          [9, 10],
      ]).astype('float32')
      expected_output = np.reshape(expected_output, (2, 2, 1))
      self.assertAllEqual(expected_output, output_image)

  @test_utils.run_v2_only
  def test_output_dtypes(self):
    inputs = np.array([[[1], [2]], [[3], [4]]], dtype='float64')
    layer = image_preprocessing.CenterCrop(2, 2)
    self.assertAllEqual(layer(inputs).dtype, 'float32')
    layer = image_preprocessing.CenterCrop(2, 2, dtype='uint8')
    self.assertAllEqual(layer(inputs).dtype, 'uint8')


@test_combinations.run_all_keras_modes(always_skip_v1=True)
class RandomCropTest(test_combinations.TestCase):

  def _run_test(self, expected_height, expected_width):
    np.random.seed(1337)
    num_samples = 2
    orig_height = 5
    orig_width = 8
    channels = 3
    kwargs = {'height': expected_height, 'width': expected_width}
    with test_utils.use_gpu():
      test_utils.layer_test(
          image_preprocessing.RandomCrop,
          kwargs=kwargs,
          input_shape=(num_samples, orig_height, orig_width, channels),
          expected_output_shape=(None, expected_height, expected_width,
                                 channels))

  def test_input_smaller_than_crop_box(self):
    np.random.seed(1337)
    height, width = 10, 8
    inp = np.random.random((12, 3, 3, 3))
    with test_utils.use_gpu():
      layer = image_preprocessing.RandomCrop(height, width)
      actual_output = layer(inp)
      # In this case, output should equal resizing with crop_to_aspect ratio.
      resize_layer = image_preprocessing.Resizing(
          height, width, crop_to_aspect_ratio=True)
      expected_output = resize_layer(inp)
      self.assertAllEqual(expected_output, actual_output)

  def test_training_with_mock(self):
    np.random.seed(1337)
    height, width = 3, 4
    height_offset = np.random.randint(low=0, high=3)
    width_offset = np.random.randint(low=0, high=5)
    mock_offset = [height_offset, width_offset]
    with test_utils.use_gpu():
      layer = image_preprocessing.RandomCrop(height, width)
      with tf.compat.v1.test.mock.patch.object(
          layer._random_generator, 'random_uniform', return_value=mock_offset):
        inp = np.random.random((12, 5, 8, 3))
        actual_output = layer(inp, training=True)
        expected_output = inp[:, height_offset:(height_offset + height),
                              width_offset:(width_offset + width), :]
        self.assertAllClose(expected_output, actual_output)

  @parameterized.named_parameters(('random_crop_4_by_6', 4, 6),
                                  ('random_crop_3_by_2', 3, 2))
  def test_random_crop_output_shape(self, expected_height, expected_width):
    self._run_test(expected_height, expected_width)

  def test_random_crop_full_height(self):
    self._run_test(5, 2)

  def test_random_crop_full_width(self):
    self._run_test(3, 8)

  def test_random_crop_full(self):
    np.random.seed(1337)
    height, width = 8, 16
    inp = np.random.random((12, 8, 16, 3))
    with test_utils.use_gpu():
      layer = image_preprocessing.RandomCrop(height, width)
      actual_output = layer(inp, training=False)
      self.assertAllClose(inp, actual_output)

  def test_predicting_with_mock_longer_height(self):
    np.random.seed(1337)
    height, width = 3, 3
    inp = np.random.random((12, 10, 6, 3))
    with test_utils.use_gpu():
      layer = image_preprocessing.RandomCrop(height, width)
      actual_output = layer(inp, training=False)
      resized_inp = tf.image.resize(inp, size=[5, 3])
      expected_output = resized_inp[:, 1:4, :, :]
      self.assertAllClose(expected_output, actual_output)

  def test_predicting_with_mock_longer_width(self):
    np.random.seed(1337)
    height, width = 4, 6
    inp = np.random.random((12, 8, 16, 3))
    with test_utils.use_gpu():
      layer = image_preprocessing.RandomCrop(height, width)
      actual_output = layer(inp, training=False)
      resized_inp = tf.image.resize(inp, size=[4, 8])
      expected_output = resized_inp[:, :, 1:7, :]
      self.assertAllClose(expected_output, actual_output)

  def test_config_with_custom_name(self):
    layer = image_preprocessing.RandomCrop(5, 5, name='image_preproc')
    config = layer.get_config()
    layer_1 = image_preprocessing.RandomCrop.from_config(config)
    self.assertEqual(layer_1.name, layer.name)

  def test_unbatched_image(self):
    np.random.seed(1337)
    inp = np.random.random((16, 16, 3))
    mock_offset = [2, 2]
    with test_utils.use_gpu():
      layer = image_preprocessing.RandomCrop(8, 8)
      with tf.compat.v1.test.mock.patch.object(
          layer._random_generator,
          'random_uniform',
          return_value=mock_offset):
        actual_output = layer(inp, training=True)
        self.assertAllClose(inp[2:10, 2:10, :], actual_output)

  @test_utils.run_v2_only
  def test_uint8_input(self):
    inputs = keras.Input((128, 128, 3), batch_size=2, dtype=tf.uint8)
    layer = image_preprocessing.RandomCrop(64, 64)
    self.assertAllEqual(layer(inputs).dtype, 'float32')

  @test_utils.run_v2_only
  def test_output_dtypes(self):
    inputs = np.array([[[1], [2]], [[3], [4]]], dtype='float64')
    layer = image_preprocessing.RandomCrop(2, 2)
    self.assertAllEqual(layer(inputs).dtype, 'float32')
    layer = image_preprocessing.RandomCrop(2, 2, dtype='uint8')
    self.assertAllEqual(layer(inputs).dtype, 'uint8')


class RescalingTest(test_combinations.TestCase):

  @test_combinations.run_all_keras_modes(always_skip_v1=True)
  def test_rescaling_base(self):
    kwargs = {'scale': 1. / 127.5, 'offset': -1.}
    test_utils.layer_test(
        image_preprocessing.Rescaling,
        kwargs=kwargs,
        input_shape=(2, 5, 6, 3),
        expected_output_shape=(None, 5, 6, 3))

  @test_utils.run_v2_only
  def test_rescaling_correctness_float(self):
    layer = image_preprocessing.Rescaling(scale=1. / 127.5, offset=-1.)
    inputs = tf.random.uniform((2, 4, 5, 3))
    outputs = layer(inputs)
    self.assertAllClose(outputs.numpy(), inputs.numpy() * (1. / 127.5) - 1)

  @test_utils.run_v2_only
  def test_rescaling_correctness_int(self):
    layer = image_preprocessing.Rescaling(scale=1. / 127.5, offset=-1)
    inputs = tf.random.uniform((2, 4, 5, 3), 0, 100, dtype='int32')
    outputs = layer(inputs)
    self.assertEqual(outputs.dtype.name, 'float32')
    self.assertAllClose(outputs.numpy(), inputs.numpy() * (1. / 127.5) - 1)

  def test_config_with_custom_name(self):
    layer = image_preprocessing.Rescaling(0.5, name='rescaling')
    config = layer.get_config()
    layer_1 = image_preprocessing.Rescaling.from_config(config)
    self.assertEqual(layer_1.name, layer.name)

  @test_combinations.run_all_keras_modes(always_skip_v1=True)
  def test_unbatched_image(self):
    layer = image_preprocessing.Rescaling(scale=1. / 127.5, offset=-1)
    inputs = tf.random.uniform((4, 5, 3))
    outputs = layer(inputs)
    self.assertAllClose(outputs.numpy(), inputs.numpy() * (1. / 127.5) - 1)

  @test_utils.run_v2_only
  def test_output_dtypes(self):
    inputs = np.array([[[1], [2]], [[3], [4]]], dtype='float64')
    layer = image_preprocessing.Rescaling(0.5)
    self.assertAllEqual(layer(inputs).dtype, 'float32')
    layer = image_preprocessing.Rescaling(0.5, dtype='uint8')
    self.assertAllEqual(layer(inputs).dtype, 'uint8')


@test_combinations.run_all_keras_modes(always_skip_v1=True)
class RandomFlipTest(test_combinations.TestCase):

  def _run_test(self, mode, expected_output=None, mock_random=None):
    np.random.seed(1337)
    num_samples = 2
    orig_height = 5
    orig_width = 8
    channels = 3
    if mock_random is None:
      mock_random = [0.0 for _ in range(num_samples)]
      if mode == 'horizontal_and_vertical':
        mock_random *= 2
    inp = np.random.random((num_samples, orig_height, orig_width, channels))
    if expected_output is None:
      expected_output = inp
      if mode == 'horizontal' or mode == 'horizontal_and_vertical':
        expected_output = np.flip(expected_output, axis=2)
      if mode == 'vertical' or mode == 'horizontal_and_vertical':
        expected_output = np.flip(expected_output, axis=1)
    with tf.compat.v1.test.mock.patch.object(
        stateless_random_ops,
        'stateless_random_uniform',
        side_effect=mock_random,
    ):
      with test_utils.use_gpu():
        layer = image_preprocessing.RandomFlip(mode)
        actual_output = layer(inp, training=True)
        self.assertAllClose(expected_output, actual_output)

  @parameterized.named_parameters(
      ('random_flip_horizontal', 'horizontal'),
      ('random_flip_vertical', 'vertical'),
      ('random_flip_both', 'horizontal_and_vertical'))
  def test_random_flip(self, mode):
    self._run_test(mode)

  def test_random_flip_horizontal_half(self):
    np.random.seed(1337)
    mock_random = [0.0, 1.0]
    input_images = np.random.random((2, 5, 8, 3)).astype(np.float32)
    expected_output = input_images.copy()
    expected_output[0, :, :, :] = np.flip(input_images[0, :, :, :], axis=1)
    self._run_test('horizontal', expected_output, mock_random)

  def test_random_flip_vertical_half(self):
    np.random.seed(1337)
    mock_random = [0.0, 1.0]
    input_images = np.random.random((2, 5, 8, 3)).astype(np.float32)
    expected_output = input_images.copy()
    expected_output[0, :, :, :] = np.flip(input_images[0, :, :, :], axis=0)
    self._run_test('vertical', expected_output, mock_random)

  def test_random_flip_inference(self):
    input_images = np.random.random((2, 5, 8, 3)).astype(np.float32)
    expected_output = input_images
    with test_utils.use_gpu():
      layer = image_preprocessing.RandomFlip()
      actual_output = layer(input_images, training=False)
      self.assertAllClose(expected_output, actual_output)

  def test_random_flip_default(self):
    input_images = np.random.random((2, 5, 8, 3)).astype(np.float32)
    expected_output = np.flip(np.flip(input_images, axis=1), axis=2)
    mock_random = [0.0, 0.0, 0.0, 0.0]
    with tf.compat.v1.test.mock.patch.object(
        stateless_random_ops,
        'stateless_random_uniform',
        side_effect=mock_random,
    ):
      with self.cached_session():
        layer = image_preprocessing.RandomFlip()
        actual_output = layer(input_images, training=True)
        self.assertAllClose(expected_output, actual_output)

  @test_utils.run_v2_only
  def test_config_with_custom_name(self):
    layer = image_preprocessing.RandomFlip(name='image_preproc')
    config = layer.get_config()
    layer_1 = image_preprocessing.RandomFlip.from_config(config)
    self.assertEqual(layer_1.name, layer.name)

  def test_random_flip_unbatched_image(self):
    input_image = np.random.random((4, 4, 1)).astype(np.float32)
    expected_output = np.flip(input_image, axis=0)
    # mock_random = np.reshape([0.], [1, 1, 1])
    with tf.compat.v1.test.mock.patch.object(
        stateless_random_ops,
        'stateless_random_uniform',
        return_value=0.,
    ):
      with self.cached_session():
        layer = image_preprocessing.RandomFlip('vertical')
        actual_output = layer(input_image, training=True)
        self.assertAllClose(expected_output, actual_output)

  @test_utils.run_v2_only
  def test_output_dtypes(self):
    inputs = np.array([[[1], [2]], [[3], [4]]], dtype='float64')
    layer = image_preprocessing.RandomFlip()
    self.assertAllEqual(layer(inputs).dtype, 'float32')
    layer = image_preprocessing.RandomFlip(dtype='uint8')
    self.assertAllEqual(layer(inputs).dtype, 'uint8')


@test_combinations.run_all_keras_modes(always_skip_v1=True)
class RandomContrastTest(test_combinations.TestCase):

  def _run_test(self, lower, upper, expected_output=None, mock_random=None):
    np.random.seed(1337)
    num_samples = 2
    orig_height = 5
    orig_width = 8
    channels = 3
    if mock_random is None:
      mock_random = 0.2
    inp = np.random.random((num_samples, orig_height, orig_width, channels))
    if expected_output is None:
      # reduce mean on height.
      inp_mean = np.mean(inp, axis=1, keepdims=True)
      # reduce mean on width.
      inp_mean = np.mean(inp_mean, axis=2, keepdims=True)
      expected_output = (inp - inp_mean) * mock_random + inp_mean
    with tf.compat.v1.test.mock.patch.object(
        stateless_random_ops,
        'stateless_random_uniform',
        return_value=mock_random,
    ):
      with test_utils.use_gpu():
        layer = image_preprocessing.RandomContrast((lower, upper))
        actual_output = layer(inp, training=True)
        self.assertAllClose(expected_output, actual_output)

  @parameterized.named_parameters(('random_contrast_2_by_5', 0.2, 0.5),
                                  ('random_contrast_2_by_13', 0.2, 1.3),
                                  ('random_contrast_5_by_2', 0.5, 0.2),
                                  ('random_contrast_10_by_10', 1.0, 1.0))
  def test_random_contrast(self, lower, upper):
    self._run_test(lower, upper)

  @parameterized.named_parameters(('random_contrast_amplitude_2', 0.2),
                                  ('random_contrast_amplitude_5', 0.5))
  def test_random_contrast_amplitude(self, amplitude):
    input_images = np.random.random((2, 5, 8, 3))
    with test_utils.use_gpu():
      layer = image_preprocessing.RandomContrast(amplitude)
      layer(input_images)

  def test_random_contrast_inference(self):
    input_images = np.random.random((2, 5, 8, 3)).astype(np.float32)
    expected_output = input_images
    with test_utils.use_gpu():
      layer = image_preprocessing.RandomContrast((0.1, 0.2))
      actual_output = layer(input_images, training=False)
      self.assertAllClose(expected_output, actual_output)

  def test_random_contrast_int_dtype(self):
    input_images = np.random.randint(low=0, high=255, size=(2, 5, 8, 3))
    with test_utils.use_gpu():
      layer = image_preprocessing.RandomContrast((0.1, 0.2))
      layer(input_images)

  def test_random_contrast_invalid_bounds(self):
    with self.assertRaises(ValueError):
      image_preprocessing.RandomContrast((-0.1, .5))

    with self.assertRaises(ValueError):
      image_preprocessing.RandomContrast((1.1, .5))

    with self.assertRaises(ValueError):
      image_preprocessing.RandomContrast((0.1, -0.2))

  @test_utils.run_v2_only
  def test_config_with_custom_name(self):
    layer = image_preprocessing.RandomContrast((.5, .6), name='image_preproc')
    config = layer.get_config()
    layer_1 = image_preprocessing.RandomContrast.from_config(config)
    self.assertEqual(layer_1.name, layer.name)

  def test_output_value_clip(self):
    input_images = np.random.random((5, 8, 3)).astype(np.float32) * 255.0
    # Give a factor range [1.0, 11.0] so that it will produce large contrast.
    layer = image_preprocessing.RandomContrast((0.0, 10.0))
    output = layer(input_images)
    self.assertLessEqual(tf.reduce_max(output), 255.0)
    self.assertGreaterEqual(tf.reduce_min(output), 0.0)

  def test_unbatched_image(self):
    np.random.seed(1337)
    mock_random = 0.2
    inp = np.random.random((4, 4, 1))
    inp_mean = np.mean(inp, axis=0, keepdims=True)
    inp_mean = np.mean(inp_mean, axis=1, keepdims=True)
    expected_output = (inp - inp_mean) * mock_random + inp_mean
    with tf.compat.v1.test.mock.patch.object(
        stateless_random_ops,
        'stateless_random_uniform',
        return_value=mock_random,
    ):
      with test_utils.use_gpu():
        layer = image_preprocessing.RandomContrast((0.2, 0.5))
        actual_output = layer(inp, training=True)
        self.assertAllClose(expected_output, actual_output)

  @test_utils.run_v2_only
  def test_output_dtypes(self):
    inputs = np.array([[[1], [2]], [[3], [4]]], dtype='float64')
    layer = image_preprocessing.RandomContrast((.5, .6))
    self.assertAllEqual(layer(inputs).dtype, 'float32')
    layer = image_preprocessing.RandomContrast((.5, .6), dtype='uint8')
    self.assertAllEqual(layer(inputs).dtype, 'uint8')


@test_combinations.run_all_keras_modes(always_skip_v1=True)
class RandomBrightnessTest(test_combinations.TestCase):

  def test_factor_input_validation(self):
    with self.assertRaisesRegex(ValueError, r'in the range \[-1.0, 1.0\]'):
      image_preprocessing.RandomBrightness(2.0)

    with self.assertRaisesRegex(ValueError, 'list of two numbers'):
      image_preprocessing.RandomBrightness([1.0])

    with self.assertRaisesRegex(ValueError, 'should be a number'):
      image_preprocessing.RandomBrightness('one')

  def test_factor_normalize(self):
    layer = image_preprocessing.RandomBrightness(1.0)
    self.assertEqual(layer._factor, [-1.0, 1.0])

    layer = image_preprocessing.RandomBrightness((0.5, 0.3))
    self.assertEqual(layer._factor, [0.3, 0.5])

    layer = image_preprocessing.RandomBrightness(-0.2)
    self.assertEqual(layer._factor, [-0.2, 0.2])

  @test_utils.run_v2_only
  def test_output_value_range(self):
    # Always scale up to 255
    layer = image_preprocessing.RandomBrightness([1.0, 1.0])
    inputs = np.random.randint(0, 255, size=(224, 224, 3))
    output = layer(inputs)
    output_min = tf.math.reduce_min(output)
    output_max = tf.math.reduce_max(output)
    self.assertEqual(output_min, 255)
    self.assertEqual(output_max, 255)

    # Always scale down to 0
    layer = image_preprocessing.RandomBrightness([-1.0, -1.0])
    inputs = np.random.randint(0, 255, size=(224, 224, 3))
    output = layer(inputs)
    output_min = tf.math.reduce_min(output)
    output_max = tf.math.reduce_max(output)
    self.assertEqual(output_min, 0)
    self.assertEqual(output_max, 0)

  def test_output(self):
    # Always scale up, but randomly between 0 ~ 255
    layer = image_preprocessing.RandomBrightness([0, 1.0])
    inputs = np.random.randint(0, 255, size=(224, 224, 3))
    output = layer(inputs)
    diff = output - inputs
    self.assertGreaterEqual(tf.math.reduce_min(diff), 0)
    self.assertGreater(tf.math.reduce_mean(diff), 0)

    # Always scale down, but randomly between 0 ~ 255
    layer = image_preprocessing.RandomBrightness([-1.0, 0.0])
    inputs = np.random.randint(0, 255, size=(224, 224, 3))
    output = layer(inputs)
    diff = output - inputs
    self.assertLessEqual(tf.math.reduce_max(diff), 0)
    self.assertLess(tf.math.reduce_mean(diff), 0)

  @test_utils.run_v2_only
  def test_scale_output(self):
    layer = image_preprocessing.RandomBrightness([0, 1.0], seed=1337)
    inputs = np.random.randint(0, 255, size=(224, 224, 3))
    output = layer(inputs)

    # Create a new layer with same seed but different value range
    layer2 = image_preprocessing.RandomBrightness(
        [0, 1.0], value_range=[0, 1], seed=1337)
    inputs2 = inputs / 255.0
    output2 = layer2(inputs2)
    # Make sure the outputs are the same, but just scaled with 255
    self.assertAllClose(output, output2 * 255.0)

  def test_different_adjustment_within_batch(self):
    layer = image_preprocessing.RandomBrightness([0.2, 0.3])
    inputs = np.zeros(shape=(2, 10, 10, 3))  # 2 images with all zeros
    output = layer(inputs)
    diff = output - inputs
    # Make sure two images gets the different adjustment
    self.assertNotAllClose(diff[0], diff[1])
    # Make sure all the pixel are the same with the same image
    image1 = output[0]
    # The reduced mean pixel value among width and height are the same as
    # any of the pixel in the image.
    self.assertAllClose(
        tf.reduce_mean(image1), image1[0, 0, 0], rtol=1e-5, atol=1e-5)

  def test_inference(self):
    layer = image_preprocessing.RandomBrightness([0, 1.0])
    inputs = np.random.randint(0, 255, size=(224, 224, 3))
    output = layer(inputs, training=False)
    self.assertAllClose(inputs, output)

  @test_utils.run_v2_only
  def test_dtype(self):
    layer = image_preprocessing.RandomBrightness([0, 1.0])
    inputs = np.random.randint(0, 255, size=(224, 224, 3))
    output = layer(inputs)
    self.assertEqual(output.dtype, tf.float32)

    layer = image_preprocessing.RandomBrightness([0, 1.0], dtype='uint8')
    output = layer(inputs)
    self.assertEqual(output.dtype, tf.uint8)

  def test_seed(self):
    layer = image_preprocessing.RandomBrightness([0, 1.0], seed=1337)
    inputs = np.random.randint(0, 255, size=(224, 224, 3))
    output_1 = layer(inputs)

    layer2 = image_preprocessing.RandomBrightness([0, 1.0], seed=1337)
    output_2 = layer2(inputs)

    self.assertAllClose(output_1, output_2)

  def test_config(self):
    layer = image_preprocessing.RandomBrightness(
        [0, 1.0], value_range=[0.0, 1.0], seed=1337)
    config = layer.get_config()
    self.assertEqual(config['factor'], [0.0, 1.0])
    self.assertEqual(config['value_range'], [0.0, 1.0])
    self.assertEqual(config['seed'], 1337)

    reconstructed_layer = image_preprocessing.RandomBrightness.from_config(
        config)
    self.assertEqual(reconstructed_layer._factor, layer._factor)
    self.assertEqual(reconstructed_layer._value_range, layer._value_range)
    self.assertEqual(reconstructed_layer._seed, layer._seed)


@test_utils.run_v2_only
@test_combinations.run_all_keras_modes(always_skip_v1=True)
class RandomTranslationTest(test_combinations.TestCase):

  def _run_test(self, height_factor, width_factor):
    np.random.seed(1337)
    num_samples = 2
    orig_height = 5
    orig_width = 8
    channels = 3
    kwargs = {'height_factor': height_factor, 'width_factor': width_factor}
    with test_utils.use_gpu():
      test_utils.layer_test(
          image_preprocessing.RandomTranslation,
          kwargs=kwargs,
          input_shape=(num_samples, orig_height, orig_width, channels),
          expected_output_shape=(None, orig_height, orig_width, channels))

  @parameterized.named_parameters(
      ('random_translate_4_by_6', .4, .6), ('random_translate_3_by_2', .3, .2),
      ('random_translate_tuple_factor', (-.5, .4), (.2, .3)))
  def test_random_translation(self, height_factor, width_factor):
    self._run_test(height_factor, width_factor)

  def test_random_translation_up_numeric_reflect(self):
    for dtype in (np.int64, np.float32):
      with test_utils.use_gpu():
        input_image = np.reshape(np.arange(0, 25), (1, 5, 5, 1)).astype(dtype)
        # Shifting by -.2 * 5 = 1 pixel.
        layer = image_preprocessing.RandomTranslation(
            height_factor=(-.2, -.2), width_factor=0.)
        output_image = layer(input_image)
        expected_output = np.asarray([
            [5, 6, 7, 8, 9],
            [10, 11, 12, 13, 14],
            [15, 16, 17, 18, 19],
            [20, 21, 22, 23, 24],
            [20, 21, 22, 23, 24],
        ]).astype(dtype)
        expected_output = np.reshape(expected_output, (1, 5, 5, 1))
        self.assertAllEqual(expected_output, output_image)

  def test_random_translation_up_numeric_constant(self):
    for dtype in (np.int64, np.float32):
      with test_utils.use_gpu():
        input_image = np.reshape(np.arange(0, 25), (1, 5, 5, 1)).astype(dtype)
        # Shifting by -.2 * 5 = 1 pixel.
        layer = image_preprocessing.RandomTranslation(
            height_factor=(-.2, -.2), width_factor=0., fill_mode='constant')
        output_image = layer(input_image)
        expected_output = np.asarray([
            [5, 6, 7, 8, 9],
            [10, 11, 12, 13, 14],
            [15, 16, 17, 18, 19],
            [20, 21, 22, 23, 24],
            [0, 0, 0, 0, 0],
        ]).astype(dtype)
        expected_output = np.reshape(expected_output, (1, 5, 5, 1))
        self.assertAllEqual(expected_output, output_image)

  def test_random_translation_down_numeric_reflect(self):
    for dtype in (np.int64, np.float32):
      with test_utils.use_gpu():
        input_image = np.reshape(np.arange(0, 25), (1, 5, 5, 1)).astype(dtype)
        # Shifting by .2 * 5 = 1 pixel.
        layer = image_preprocessing.RandomTranslation(
            height_factor=(.2, .2), width_factor=0.)
        output_image = layer(input_image)
        expected_output = np.asarray([
            [0, 1, 2, 3, 4],
            [0, 1, 2, 3, 4],
            [5, 6, 7, 8, 9],
            [10, 11, 12, 13, 14],
            [15, 16, 17, 18, 19],
        ]).astype(dtype)
        expected_output = np.reshape(expected_output, (1, 5, 5, 1))
        self.assertAllEqual(expected_output, output_image)

  def test_random_translation_asymmetric_size_numeric_reflect(self):
    for dtype in (np.int64, np.float32):
      with test_utils.use_gpu():
        input_image = np.reshape(np.arange(0, 16), (1, 8, 2, 1)).astype(dtype)
        # Shifting by .5 * 8 = 1 pixel.
        layer = image_preprocessing.RandomTranslation(
            height_factor=(.5, .5), width_factor=0.)
        output_image = layer(input_image)
        # pyformat: disable
        expected_output = np.asarray([
            [6, 7],
            [4, 5],
            [2, 3],
            [0, 1],
            [0, 1],
            [2, 3],
            [4, 5],
            [6, 7],
        ]).astype(dtype)
        # pyformat: enable
        expected_output = np.reshape(expected_output, (1, 8, 2, 1))
        self.assertAllEqual(expected_output, output_image)

  def test_random_translation_down_numeric_constant(self):
    for dtype in (np.int64, np.float32):
      with test_utils.use_gpu():
        input_image = np.reshape(np.arange(0, 25), (1, 5, 5, 1)).astype(dtype)
        # Shifting by -.2 * 5 = 1 pixel.
        layer = image_preprocessing.RandomTranslation(
            height_factor=(.2, .2), width_factor=0., fill_mode='constant')
        output_image = layer(input_image)
        expected_output = np.asarray([
            [0, 0, 0, 0, 0],
            [0, 1, 2, 3, 4],
            [5, 6, 7, 8, 9],
            [10, 11, 12, 13, 14],
            [15, 16, 17, 18, 19],
        ]).astype(dtype)
        expected_output = np.reshape(expected_output, (1, 5, 5, 1))
        self.assertAllEqual(expected_output, output_image)

  def test_random_translation_left_numeric_reflect(self):
    for dtype in (np.int64, np.float32):
      with test_utils.use_gpu():
        input_image = np.reshape(np.arange(0, 25), (1, 5, 5, 1)).astype(dtype)
        # Shifting by .2 * 5 = 1 pixel.
        layer = image_preprocessing.RandomTranslation(
            height_factor=0., width_factor=(-.2, -.2))
        output_image = layer(input_image)
        expected_output = np.asarray([
            [1, 2, 3, 4, 4],
            [6, 7, 8, 9, 9],
            [11, 12, 13, 14, 14],
            [16, 17, 18, 19, 19],
            [21, 22, 23, 24, 24],
        ]).astype(dtype)
        expected_output = np.reshape(expected_output, (1, 5, 5, 1))
        self.assertAllEqual(expected_output, output_image)

  def test_random_translation_left_numeric_constant(self):
    for dtype in (np.int64, np.float32):
      with test_utils.use_gpu():
        input_image = np.reshape(np.arange(0, 25), (1, 5, 5, 1)).astype(dtype)
        # Shifting by -.2 * 5 = 1 pixel.
        layer = image_preprocessing.RandomTranslation(
            height_factor=0., width_factor=(-.2, -.2), fill_mode='constant')
        output_image = layer(input_image)
        expected_output = np.asarray([
            [1, 2, 3, 4, 0],
            [6, 7, 8, 9, 0],
            [11, 12, 13, 14, 0],
            [16, 17, 18, 19, 0],
            [21, 22, 23, 24, 0],
        ]).astype(dtype)
        expected_output = np.reshape(expected_output, (1, 5, 5, 1))
        self.assertAllEqual(expected_output, output_image)

  def test_random_translation_inference(self):
    input_images = np.random.random((2, 5, 8, 3)).astype(np.float32)
    expected_output = input_images
    with test_utils.use_gpu():
      layer = image_preprocessing.RandomTranslation(.5, .5)
      actual_output = layer(input_images, training=False)
      self.assertAllClose(expected_output, actual_output)

  @test_utils.run_v2_only
  def test_config_with_custom_name(self):
    layer = image_preprocessing.RandomTranslation(.5, .6, name='image_preproc')
    config = layer.get_config()
    layer_1 = image_preprocessing.RandomTranslation.from_config(config)
    self.assertEqual(layer_1.name, layer.name)

  def test_unbatched_image(self):
    with test_utils.use_gpu():
      input_image = np.reshape(np.arange(0, 25), (5, 5, 1)).astype(np.int64)
      # Shifting by -.2 * 5 = 1 pixel.
      layer = image_preprocessing.RandomTranslation(
          height_factor=(-.2, -.2), width_factor=0.)
      output_image = layer(input_image)
      expected_output = np.asarray([
          [5, 6, 7, 8, 9],
          [10, 11, 12, 13, 14],
          [15, 16, 17, 18, 19],
          [20, 21, 22, 23, 24],
          [20, 21, 22, 23, 24],
      ]).astype(np.int64)
      expected_output = np.reshape(expected_output, (5, 5, 1))
      self.assertAllEqual(expected_output, output_image)

  @test_utils.run_v2_only
  def test_output_dtypes(self):
    inputs = np.array([[[1], [2]], [[3], [4]]], dtype='float64')
    layer = image_preprocessing.RandomTranslation(.5, .6)
    self.assertAllEqual(layer(inputs).dtype, 'float32')
    layer = image_preprocessing.RandomTranslation(.5, .6, dtype='uint8')
    self.assertAllEqual(layer(inputs).dtype, 'uint8')


@test_combinations.run_all_keras_modes(always_skip_v1=True)
class RandomTransformTest(test_combinations.TestCase):

  def _run_random_transform_with_mock(self,
                                      transform_matrix,
                                      expected_output,
                                      mode,
                                      fill_value=0.0,
                                      interpolation='bilinear'):
    inp = np.arange(15).reshape((1, 5, 3, 1)).astype(np.float32)
    with self.cached_session():
      output = image_preprocessing.transform(
          inp,
          transform_matrix,
          fill_mode=mode,
          fill_value=fill_value,
          interpolation=interpolation)
    self.assertAllClose(expected_output, output)

  def test_random_translation_reflect(self):
    # reflected output is (dcba|abcd|dcba)

    # Test down shift by 1.
    # pyformat: disable
    expected_output = np.asarray(
        [[0., 1., 2.],
         [0., 1., 2.],
         [3., 4., 5.],
         [6., 7., 8],
         [9., 10., 11]]).reshape((1, 5, 3, 1)).astype(np.float32)
    # pyformat: enable
    transform_matrix = np.asarray([[1., 0., 0., 0., 1., -1., 0., 0.]])
    self._run_random_transform_with_mock(transform_matrix, expected_output,
                                         'reflect')

    # Test up shift by 1.
    # pyformat: disable
    expected_output = np.asarray(
        [[3., 4., 5.],
         [6., 7., 8],
         [9., 10., 11.],
         [12., 13., 14.],
         [12., 13., 14.]]).reshape((1, 5, 3, 1)).astype(np.float32)
    # pyformat: enable
    transform_matrix = np.asarray([[1., 0., 0., 0., 1., 1., 0., 0.]])
    self._run_random_transform_with_mock(transform_matrix, expected_output,
                                         'reflect')

    # Test left shift by 1.
    # reflected output is (dcba|abcd|dcba)
    # pyformat: disable
    expected_output = np.asarray(
        [[1., 2., 2.],
         [4., 5., 5.],
         [7., 8., 8.],
         [10., 11., 11.],
         [13., 14., 14.]]).reshape((1, 5, 3, 1)).astype(np.float32)
    # pyformat: enable
    transform_matrix = np.asarray([[1., 0., 1., 0., 1., 0., 0., 0.]])
    self._run_random_transform_with_mock(transform_matrix, expected_output,
                                         'reflect')

    # Test right shift by 1.
    # pyformat: disable
    expected_output = np.asarray(
        [[0., 0., 1.],
         [3., 3., 4],
         [6., 6., 7.],
         [9., 9., 10.],
         [12., 12., 13.]]).reshape((1, 5, 3, 1)).astype(np.float32)
    # pyformat: enable
    transform_matrix = np.asarray([[1., 0., -1., 0., 1., 0., 0., 0.]])
    self._run_random_transform_with_mock(transform_matrix, expected_output,
                                         'reflect')

  def test_random_translation_wrap(self):
    # warpped output is (abcd|abcd|abcd)

    # Test down shift by 1.
    # pyformat: disable
    expected_output = np.asarray(
        [[12., 13., 14.],
         [0., 1., 2.],
         [3., 4., 5.],
         [6., 7., 8],
         [9., 10., 11]]).reshape((1, 5, 3, 1)).astype(np.float32)
    # pyformat: enable
    transform_matrix = np.asarray([[1., 0., 0., 0., 1., -1., 0., 0.]])
    self._run_random_transform_with_mock(transform_matrix, expected_output,
                                         'wrap')

    # Test up shift by 1.
    # pyformat: disable
    expected_output = np.asarray(
        [[3., 4., 5.],
         [6., 7., 8],
         [9., 10., 11.],
         [12., 13., 14.],
         [0., 1., 2.]]).reshape((1, 5, 3, 1)).astype(np.float32)
    # pyformat: enable
    transform_matrix = np.asarray([[1., 0., 0., 0., 1., 1., 0., 0.]])
    self._run_random_transform_with_mock(transform_matrix, expected_output,
                                         'wrap')

    # Test left shift by 1.
    # pyformat: disable
    expected_output = np.asarray(
        [[1., 2., 0.],
         [4., 5., 3.],
         [7., 8., 6.],
         [10., 11., 9.],
         [13., 14., 12.]]).reshape((1, 5, 3, 1)).astype(np.float32)
    # pyformat: enable
    transform_matrix = np.asarray([[1., 0., 1., 0., 1., 0., 0., 0.]])
    self._run_random_transform_with_mock(transform_matrix, expected_output,
                                         'wrap')

    # Test right shift by 1.
    # pyformat: disable
    expected_output = np.asarray(
        [[2., 0., 1.],
         [5., 3., 4],
         [8., 6., 7.],
         [11., 9., 10.],
         [14., 12., 13.]]).reshape((1, 5, 3, 1)).astype(np.float32)
    # pyformat: enable
    transform_matrix = np.asarray([[1., 0., -1., 0., 1., 0., 0., 0.]])
    self._run_random_transform_with_mock(transform_matrix, expected_output,
                                         'wrap')

  def test_random_translation_nearest(self):
    # nearest output is (aaaa|abcd|dddd)

    # Test down shift by 1.
    # pyformat: disable
    expected_output = np.asarray(
        [[0., 1., 2.],
         [0., 1., 2.],
         [3., 4., 5.],
         [6., 7., 8],
         [9., 10., 11]]).reshape((1, 5, 3, 1)).astype(np.float32)
    # pyformat: enable
    transform_matrix = np.asarray([[1., 0., 0., 0., 1., -1., 0., 0.]])
    self._run_random_transform_with_mock(transform_matrix, expected_output,
                                         'nearest')

    # Test up shift by 1.
    # pyformat: disable
    expected_output = np.asarray(
        [[3., 4., 5.],
         [6., 7., 8],
         [9., 10., 11.],
         [12., 13., 14.],
         [12., 13., 14.]]).reshape((1, 5, 3, 1)).astype(np.float32)
    # pyformat: enable
    transform_matrix = np.asarray([[1., 0., 0., 0., 1., 1., 0., 0.]])
    self._run_random_transform_with_mock(transform_matrix, expected_output,
                                         'nearest')

    # Test left shift by 1.
    # pyformat: disable
    expected_output = np.asarray(
        [[1., 2., 2.],
         [4., 5., 5.],
         [7., 8., 8.],
         [10., 11., 11.],
         [13., 14., 14.]]).reshape((1, 5, 3, 1)).astype(np.float32)
    # pyformat: enable
    transform_matrix = np.asarray([[1., 0., 1., 0., 1., 0., 0., 0.]])
    self._run_random_transform_with_mock(transform_matrix, expected_output,
                                         'nearest')

    # Test right shift by 1.
    # pyformat: disable
    expected_output = np.asarray(
        [[0., 0., 1.],
         [3., 3., 4],
         [6., 6., 7.],
         [9., 9., 10.],
         [12., 12., 13.]]).reshape((1, 5, 3, 1)).astype(np.float32)
    # pyformat: enable
    transform_matrix = np.asarray([[1., 0., -1., 0., 1., 0., 0., 0.]])
    self._run_random_transform_with_mock(transform_matrix, expected_output,
                                         'nearest')

  def test_random_translation_constant_0(self):
    # constant output is (0000|abcd|0000)

    # Test down shift by 1.
    # pyformat: disable
    expected_output = np.asarray(
        [[0., 0., 0.],
         [0., 1., 2.],
         [3., 4., 5.],
         [6., 7., 8],
         [9., 10., 11]]).reshape((1, 5, 3, 1)).astype(np.float32)
    # pyformat: enable
    transform_matrix = np.asarray([[1., 0., 0., 0., 1., -1., 0., 0.]])
    self._run_random_transform_with_mock(transform_matrix, expected_output,
                                         'constant')

    # Test up shift by 1.
    # pyformat: disable
    expected_output = np.asarray(
        [[3., 4., 5.],
         [6., 7., 8],
         [9., 10., 11.],
         [12., 13., 14.],
         [0., 0., 0.]]).reshape((1, 5, 3, 1)).astype(np.float32)
    # pyformat: enable
    transform_matrix = np.asarray([[1., 0., 0., 0., 1., 1., 0., 0.]])
    self._run_random_transform_with_mock(transform_matrix, expected_output,
                                         'constant')

    # Test left shift by 1.
    # pyformat: disable
    expected_output = np.asarray(
        [[1., 2., 0.],
         [4., 5., 0.],
         [7., 8., 0.],
         [10., 11., 0.],
         [13., 14., 0.]]).reshape((1, 5, 3, 1)).astype(np.float32)
    # pyformat: enable
    transform_matrix = np.asarray([[1., 0., 1., 0., 1., 0., 0., 0.]])
    self._run_random_transform_with_mock(transform_matrix, expected_output,
                                         'constant')

    # Test right shift by 1.
    # pyformat: disable
    expected_output = np.asarray(
        [[0., 0., 1.],
         [0., 3., 4],
         [0., 6., 7.],
         [0., 9., 10.],
         [0., 12., 13.]]).reshape((1, 5, 3, 1)).astype(np.float32)
    # pyformat: enable
    transform_matrix = np.asarray([[1., 0., -1., 0., 1., 0., 0., 0.]])
    self._run_random_transform_with_mock(transform_matrix, expected_output,
                                         'constant')

  def test_random_translation_constant_1(self):
    with tf.compat.forward_compatibility_horizon(2020, 8, 6):
      # constant output is (1111|abcd|1111)

      # Test down shift by 1.
      # pyformat: disable
      expected_output = np.asarray(
          [[1., 1., 1.],
           [0., 1., 2.],
           [3., 4., 5.],
           [6., 7., 8],
           [9., 10., 11]]).reshape((1, 5, 3, 1)).astype(np.float32)
      # pyformat: enable
      transform_matrix = np.asarray([[1., 0., 0., 0., 1., -1., 0., 0.]])
      self._run_random_transform_with_mock(
          transform_matrix, expected_output, 'constant', fill_value=1.0)

      # Test up shift by 1.
      # pyformat: disable
      expected_output = np.asarray(
          [[3., 4., 5.],
           [6., 7., 8],
           [9., 10., 11.],
           [12., 13., 14.],
           [1., 1., 1.]]).reshape((1, 5, 3, 1)).astype(np.float32)
      # pyformat: enable
      transform_matrix = np.asarray([[1., 0., 0., 0., 1., 1., 0., 0.]])
      self._run_random_transform_with_mock(
          transform_matrix, expected_output, 'constant', fill_value=1.0)

      # Test left shift by 1.
      # pyformat: disable
      expected_output = np.asarray(
          [[1., 2., 1.],
           [4., 5., 1.],
           [7., 8., 1.],
           [10., 11., 1.],
           [13., 14., 1.]]).reshape((1, 5, 3, 1)).astype(np.float32)
      # pyformat: enable
      transform_matrix = np.asarray([[1., 0., 1., 0., 1., 0., 0., 0.]])
      self._run_random_transform_with_mock(
          transform_matrix, expected_output, 'constant', fill_value=1.0)

      # Test right shift by 1.
      # pyformat: disable
      expected_output = np.asarray(
          [[1., 0., 1.],
           [1., 3., 4],
           [1., 6., 7.],
           [1., 9., 10.],
           [1., 12., 13.]]).reshape((1, 5, 3, 1)).astype(np.float32)
      # pyformat: enable
      transform_matrix = np.asarray([[1., 0., -1., 0., 1., 0., 0., 0.]])
      self._run_random_transform_with_mock(
          transform_matrix, expected_output, 'constant', fill_value=1.0)

  def test_random_translation_nearest_interpolation(self):
    # nearest output is (aaaa|abcd|dddd)

    # Test down shift by 1.
    # pyformat: disable
    expected_output = np.asarray(
        [[0., 0., 0.],
         [0., 1., 2.],
         [3., 4., 5.],
         [6., 7., 8],
         [9., 10., 11]]).reshape((1, 5, 3, 1)).astype(np.float32)
    # pyformat: enable
    transform_matrix = np.asarray([[1., 0., 0., 0., 1., -1., 0., 0.]])
    self._run_random_transform_with_mock(
        transform_matrix,
        expected_output,
        mode='constant',
        interpolation='nearest')

    # Test up shift by 1.
    # pyformat: disable
    expected_output = np.asarray(
        [[3., 4., 5.],
         [6., 7., 8],
         [9., 10., 11.],
         [12., 13., 14.],
         [0., 0., 0.]]).reshape((1, 5, 3, 1)).astype(np.float32)
    # pyformat: enable
    transform_matrix = np.asarray([[1., 0., 0., 0., 1., 1., 0., 0.]])
    self._run_random_transform_with_mock(
        transform_matrix,
        expected_output,
        mode='constant',
        interpolation='nearest')

    # Test left shift by 1.
    # pyformat: disable
    expected_output = np.asarray(
        [[1., 2., 0.],
         [4., 5., 0.],
         [7., 8., 0.],
         [10., 11., 0.],
         [13., 14., 0.]]).reshape((1, 5, 3, 1)).astype(np.float32)
    # pyformat: enable
    transform_matrix = np.asarray([[1., 0., 1., 0., 1., 0., 0., 0.]])
    self._run_random_transform_with_mock(
        transform_matrix,
        expected_output,
        mode='constant',
        interpolation='nearest')

    # Test right shift by 1.
    # pyformat: disable
    expected_output = np.asarray(
        [[0., 0., 1.],
         [0., 3., 4],
         [0., 6., 7.],
         [0., 9., 10.],
         [0., 12., 13.]]).reshape((1, 5, 3, 1)).astype(np.float32)
    # pyformat: enable
    transform_matrix = np.asarray([[1., 0., -1., 0., 1., 0., 0., 0.]])
    self._run_random_transform_with_mock(
        transform_matrix,
        expected_output,
        mode='constant',
        interpolation='nearest')


@test_combinations.run_all_keras_modes(always_skip_v1=True)
class RandomRotationTest(test_combinations.TestCase):

  def _run_test(self, factor):
    np.random.seed(1337)
    num_samples = 2
    orig_height = 5
    orig_width = 8
    channels = 3
    kwargs = {'factor': factor}
    with test_utils.use_gpu():
      test_utils.layer_test(
          image_preprocessing.RandomRotation,
          kwargs=kwargs,
          input_shape=(num_samples, orig_height, orig_width, channels),
          expected_output_shape=(None, orig_height, orig_width, channels))

  @parameterized.named_parameters(('random_rotate_4', .4),
                                  ('random_rotate_3', .3),
                                  ('random_rotate_tuple_factor', (-.5, .4)))
  def test_random_rotation(self, factor):
    self._run_test(factor)

  def test_random_rotation_inference(self):
    input_images = np.random.random((2, 5, 8, 3)).astype(np.float32)
    expected_output = input_images
    with test_utils.use_gpu():
      layer = image_preprocessing.RandomRotation(.5)
      actual_output = layer(input_images, training=False)
      self.assertAllClose(expected_output, actual_output)

  def test_distribution_strategy(self):
    """Tests that RandomRotation can be created within distribution strategies."""
    input_images = np.random.random((2, 5, 8, 3)).astype(np.float32)
    with test_utils.use_gpu():
      strat = tf.distribute.MirroredStrategy(devices=['cpu', 'gpu'])
      with strat.scope():
        layer = image_preprocessing.RandomRotation(.5)
        output = strat.run(lambda: layer(input_images, training=True))
      values = output.values
      self.assertAllEqual(2, len(values))

  @test_utils.run_v2_only
  def test_config_with_custom_name(self):
    layer = image_preprocessing.RandomRotation(.5, name='image_preproc')
    config = layer.get_config()
    layer_1 = image_preprocessing.RandomRotation.from_config(config)
    self.assertEqual(layer_1.name, layer.name)

  def test_unbatched_image(self):
    with test_utils.use_gpu():
      input_image = np.reshape(np.arange(0, 25), (5, 5, 1)).astype(np.float32)
      # 180 rotation.
      layer = image_preprocessing.RandomRotation(factor=(0.5, 0.5))
      output_image = layer(input_image)
      expected_output = np.asarray([
          [24, 23, 22, 21, 20],
          [19, 18, 17, 16, 15],
          [14, 13, 12, 11, 10],
          [9, 8, 7, 6, 5],
          [4, 3, 2, 1, 0],
      ]).astype(np.float32)
      expected_output = np.reshape(expected_output, (5, 5, 1))
      self.assertAllClose(expected_output, output_image)

  @test_utils.run_v2_only
  def test_output_dtypes(self):
    inputs = np.array([[[1], [2]], [[3], [4]]], dtype='float64')
    layer = image_preprocessing.RandomRotation(.5)
    self.assertAllEqual(layer(inputs).dtype, 'float32')
    layer = image_preprocessing.RandomRotation(.5, dtype='uint8')
    self.assertAllEqual(layer(inputs).dtype, 'uint8')


@test_combinations.run_all_keras_modes(always_skip_v1=True)
class RandomZoomTest(test_combinations.TestCase):

  def _run_test(self, height_factor, width_factor):
    np.random.seed(1337)
    num_samples = 2
    orig_height = 5
    orig_width = 8
    channels = 3
    kwargs = {'height_factor': height_factor, 'width_factor': width_factor}
    with test_utils.use_gpu():
      test_utils.layer_test(
          image_preprocessing.RandomZoom,
          kwargs=kwargs,
          input_shape=(num_samples, orig_height, orig_width, channels),
          expected_output_shape=(None, orig_height, orig_width, channels))

  @parameterized.named_parameters(
      ('random_zoom_4_by_6', -.4, -.6), ('random_zoom_2_by_3', -.2, -.3),
      ('random_zoom_tuple_factor', (-.4, -.5), (-.2, -.3)))
  def test_random_zoom_in(self, height_factor, width_factor):
    self._run_test(height_factor, width_factor)

  @parameterized.named_parameters(
      ('random_zoom_4_by_6', .4, .6), ('random_zoom_2_by_3', .2, .3),
      ('random_zoom_tuple_factor', (.4, .5), (.2, .3)))
  def test_random_zoom_out(self, height_factor, width_factor):
    self._run_test(height_factor, width_factor)

  def test_random_zoom_in_numeric(self):
    for dtype in (np.int64, np.float32):
      with test_utils.use_gpu():
        input_image = np.reshape(np.arange(0, 25), (5, 5, 1)).astype(dtype)
        layer = image_preprocessing.RandomZoom((-.5, -.5), (-.5, -.5),
                                               interpolation='nearest')
        output_image = layer(np.expand_dims(input_image, axis=0))
        expected_output = np.asarray([
            [6, 7, 7, 8, 8],
            [11, 12, 12, 13, 13],
            [11, 12, 12, 13, 13],
            [16, 17, 17, 18, 18],
            [16, 17, 17, 18, 18],
        ]).astype(dtype)
        expected_output = np.reshape(expected_output, (1, 5, 5, 1))
        self.assertAllEqual(expected_output, output_image)

  def test_random_zoom_out_numeric(self):
    for dtype in (np.int64, np.float32):
      with test_utils.use_gpu():
        input_image = np.reshape(np.arange(0, 25), (5, 5, 1)).astype(dtype)
        layer = image_preprocessing.RandomZoom((.5, .5), (.8, .8),
                                               fill_mode='constant',
                                               interpolation='nearest')
        output_image = layer(np.expand_dims(input_image, axis=0))
        expected_output = np.asarray([
            [0, 0, 0, 0, 0],
            [0, 5, 7, 9, 0],
            [0, 10, 12, 14, 0],
            [0, 20, 22, 24, 0],
            [0, 0, 0, 0, 0],
        ]).astype(dtype)
        expected_output = np.reshape(expected_output, (1, 5, 5, 1))
        self.assertAllEqual(expected_output, output_image)

  def test_random_zoom_out_numeric_preserve_aspect_ratio(self):
    for dtype in (np.int64, np.float32):
      with test_utils.use_gpu():
        input_image = np.reshape(np.arange(0, 25), (5, 5, 1)).astype(dtype)
        layer = image_preprocessing.RandomZoom((.5, .5),
                                               fill_mode='constant',
                                               interpolation='nearest')
        output_image = layer(np.expand_dims(input_image, axis=0))
        expected_output = np.asarray([
            [0, 0, 0, 0, 0],
            [0, 6, 7, 9, 0],
            [0, 11, 12, 14, 0],
            [0, 21, 22, 24, 0],
            [0, 0, 0, 0, 0],
        ]).astype(dtype)
        expected_output = np.reshape(expected_output, (1, 5, 5, 1))
        self.assertAllEqual(expected_output, output_image)

  def test_random_zoom_inference(self):
    input_images = np.random.random((2, 5, 8, 3)).astype(np.float32)
    expected_output = input_images
    with test_utils.use_gpu():
      layer = image_preprocessing.RandomZoom(.5, .5)
      actual_output = layer(input_images, training=False)
      self.assertAllClose(expected_output, actual_output)

  @test_utils.run_v2_only
  def test_config_with_custom_name(self):
    layer = image_preprocessing.RandomZoom(.5, .6, name='image_preproc')
    config = layer.get_config()
    layer_1 = image_preprocessing.RandomZoom.from_config(config)
    self.assertEqual(layer_1.name, layer.name)

  def test_unbatched_image(self):
    with test_utils.use_gpu():
      input_image = np.reshape(np.arange(0, 25), (5, 5, 1)).astype(np.int64)
      layer = image_preprocessing.RandomZoom((-.5, -.5), (-.5, -.5),
                                             interpolation='nearest')
      output_image = layer(input_image)
      expected_output = np.asarray([
          [6, 7, 7, 8, 8],
          [11, 12, 12, 13, 13],
          [11, 12, 12, 13, 13],
          [16, 17, 17, 18, 18],
          [16, 17, 17, 18, 18],
      ]).astype(np.int64)
      expected_output = np.reshape(expected_output, (5, 5, 1))
      self.assertAllEqual(expected_output, output_image)

  @test_utils.run_v2_only
  def test_output_dtypes(self):
    inputs = np.array([[[1], [2]], [[3], [4]]], dtype='float64')
    layer = image_preprocessing.RandomZoom(.5, .5)
    self.assertAllEqual(layer(inputs).dtype, 'float32')
    layer = image_preprocessing.RandomZoom(.5, .5, dtype='uint8')
    self.assertAllEqual(layer(inputs).dtype, 'uint8')


@test_combinations.run_all_keras_modes(always_skip_v1=True)
class RandomHeightTest(test_combinations.TestCase):

  def _run_test(self, factor):
    np.random.seed(1337)
    num_samples = 2
    orig_height = 5
    orig_width = 8
    channels = 3
    with test_utils.use_gpu():
      img = np.random.random((num_samples, orig_height, orig_width, channels))
      layer = image_preprocessing.RandomHeight(factor)
      img_out = layer(img, training=True)
      self.assertEqual(img_out.shape[0], 2)
      self.assertEqual(img_out.shape[2], 8)
      self.assertEqual(img_out.shape[3], 3)

  @parameterized.named_parameters(('random_height_4_by_6', (.4, .6)),
                                  ('random_height_3_by_2', (-.3, .2)),
                                  ('random_height_3', .3))
  def test_random_height_basic(self, factor):
    self._run_test(factor)

  def test_valid_random_height(self):
    # need (maxval - minval) * rnd + minval = 0.6
    mock_factor = 0.6
    with test_utils.use_gpu():
      img = np.random.random((12, 5, 8, 3))
      layer = image_preprocessing.RandomHeight(.4)
      with tf.compat.v1.test.mock.patch.object(
          layer._random_generator, 'random_uniform', return_value=mock_factor):
        img_out = layer(img, training=True)
        self.assertEqual(img_out.shape[1], 3)

  def test_random_height_longer_numeric(self):
    for dtype in (np.int64, np.float32):
      with test_utils.use_gpu():
        input_image = np.reshape(np.arange(0, 6), (2, 3, 1)).astype(dtype)
        layer = image_preprocessing.RandomHeight(factor=(1., 1.))
        # Return type of RandomHeight() is float32 if `interpolation` is not
        # set to `ResizeMethod.NEAREST_NEIGHBOR`; cast `layer` to desired dtype.
        output_image = tf.cast(
            layer(np.expand_dims(input_image, axis=0)), dtype=dtype)
        # pyformat: disable
        expected_output = np.asarray([
            [0, 1, 2],
            [0.75, 1.75, 2.75],
            [2.25, 3.25, 4.25],
            [3, 4, 5]
        ]).astype(dtype)
        # pyformat: enable
        expected_output = np.reshape(expected_output, (1, 4, 3, 1))
        self.assertAllEqual(expected_output, output_image)

  def test_random_height_shorter_numeric(self):
    for dtype in (np.int64, np.float32):
      with test_utils.use_gpu():
        input_image = np.reshape(np.arange(0, 8), (4, 2, 1)).astype(dtype)
        layer = image_preprocessing.RandomHeight(
            factor=(-.5, -.5), interpolation='nearest')
        output_image = layer(np.expand_dims(input_image, axis=0))
        # pyformat: disable
        expected_output = np.asarray([
            [2, 3],
            [6, 7]
        ]).astype(dtype)
        # pyformat: enable
        expected_output = np.reshape(expected_output, (1, 2, 2, 1))
        self.assertAllEqual(expected_output, output_image)

  def test_random_height_invalid_factor(self):
    with self.assertRaises(ValueError):
      image_preprocessing.RandomHeight((-1.5, .4))

  def test_random_height_inference(self):
    input_images = np.random.random((2, 5, 8, 3)).astype(np.float32)
    expected_output = input_images
    with test_utils.use_gpu():
      layer = image_preprocessing.RandomHeight(.5)
      actual_output = layer(input_images, training=False)
      self.assertAllClose(expected_output, actual_output)

  @test_utils.run_v2_only
  def test_config_with_custom_name(self):
    layer = image_preprocessing.RandomHeight(.5, name='image_preproc')
    config = layer.get_config()
    layer_1 = image_preprocessing.RandomHeight.from_config(config)
    self.assertEqual(layer_1.name, layer.name)

  def test_unbatched_image(self):
    # need (maxval - minval) * rnd + minval = 0.6
    mock_factor = 0.6
    with test_utils.use_gpu():
      img = np.random.random((5, 8, 3))
      layer = image_preprocessing.RandomHeight(.4)
      with tf.compat.v1.test.mock.patch.object(
          layer._random_generator, 'random_uniform', return_value=mock_factor):
        img_out = layer(img, training=True)
        self.assertEqual(img_out.shape[0], 3)

  @test_utils.run_v2_only
  def test_output_dtypes(self):
    inputs = np.array([[[1], [2]], [[3], [4]]], dtype='float64')
    layer = image_preprocessing.RandomHeight(.2)
    self.assertAllEqual(layer(inputs).dtype, 'float32')
    layer = image_preprocessing.RandomHeight(.2, dtype='uint8')
    self.assertAllEqual(layer(inputs).dtype, 'uint8')


@test_combinations.run_all_keras_modes(always_skip_v1=True)
class RandomWidthTest(test_combinations.TestCase):

  def _run_test(self, factor):
    np.random.seed(1337)
    num_samples = 2
    orig_height = 5
    orig_width = 8
    channels = 3
    with test_utils.use_gpu():
      img = np.random.random((num_samples, orig_height, orig_width, channels))
      layer = image_preprocessing.RandomWidth(factor)
      img_out = layer(img, training=True)
      self.assertEqual(img_out.shape[0], 2)
      self.assertEqual(img_out.shape[1], 5)
      self.assertEqual(img_out.shape[3], 3)

  @parameterized.named_parameters(('random_width_4_by_6', (.4, .6)),
                                  ('random_width_3_by_2', (-.3, .2)),
                                  ('random_width_3', .3))
  def test_random_width_basic(self, factor):
    self._run_test(factor)

  def test_valid_random_width(self):
    # need (maxval - minval) * rnd + minval = 0.6
    mock_factor = 0.6
    with test_utils.use_gpu():
      img = np.random.random((12, 8, 5, 3))
      layer = image_preprocessing.RandomWidth(.4)
      with tf.compat.v1.test.mock.patch.object(
          layer._random_generator, 'random_uniform', return_value=mock_factor):
        img_out = layer(img, training=True)
        self.assertEqual(img_out.shape[2], 3)

  def test_random_width_longer_numeric(self):
    for dtype in (np.int64, np.float32):
      with test_utils.use_gpu():
        input_image = np.reshape(np.arange(0, 6), (3, 2, 1)).astype(dtype)
        layer = image_preprocessing.RandomWidth(factor=(1., 1.))
        # Return type of RandomWidth() is float32 if `interpolation` is not
        # set to `ResizeMethod.NEAREST_NEIGHBOR`; cast `layer` to desired dtype.
        output_image = tf.cast(
            layer(np.expand_dims(input_image, axis=0)), dtype=dtype)
        # pyformat: disable
        expected_output = np.asarray([
            [0, 0.25, 0.75, 1],
            [2, 2.25, 2.75, 3],
            [4, 4.25, 4.75, 5]
        ]).astype(dtype)
        # pyformat: enable
        expected_output = np.reshape(expected_output, (1, 3, 4, 1))
        self.assertAllEqual(expected_output, output_image)

  def test_random_width_shorter_numeric(self):
    for dtype in (np.int64, np.float32):
      with test_utils.use_gpu():
        input_image = np.reshape(np.arange(0, 8), (2, 4, 1)).astype(dtype)
        layer = image_preprocessing.RandomWidth(
            factor=(-.5, -.5), interpolation='nearest')
        output_image = layer(np.expand_dims(input_image, axis=0))
        # pyformat: disable
        expected_output = np.asarray([
            [1, 3],
            [5, 7]
        ]).astype(dtype)
        # pyformat: enable
        expected_output = np.reshape(expected_output, (1, 2, 2, 1))
        self.assertAllEqual(expected_output, output_image)

  def test_random_width_invalid_factor(self):
    with self.assertRaises(ValueError):
      image_preprocessing.RandomWidth((-1.5, .4))

  def test_random_width_inference(self):
    input_images = np.random.random((2, 5, 8, 3)).astype(np.float32)
    expected_output = input_images
    with test_utils.use_gpu():
      layer = image_preprocessing.RandomWidth(.5)
      actual_output = layer(input_images, training=False)
      self.assertAllClose(expected_output, actual_output)

  @test_utils.run_v2_only
  def test_config_with_custom_name(self):
    layer = image_preprocessing.RandomWidth(.5, name='image_preproc')
    config = layer.get_config()
    layer_1 = image_preprocessing.RandomWidth.from_config(config)
    self.assertEqual(layer_1.name, layer.name)

  def test_unbatched_image(self):
    # need (maxval - minval) * rnd + minval = 0.6
    mock_factor = 0.6
    with test_utils.use_gpu():
      img = np.random.random((8, 5, 3))
      layer = image_preprocessing.RandomWidth(.4)
      with tf.compat.v1.test.mock.patch.object(
          layer._random_generator, 'random_uniform', return_value=mock_factor):
        img_out = layer(img, training=True)
        self.assertEqual(img_out.shape[1], 3)

  @test_utils.run_v2_only
  def test_output_dtypes(self):
    inputs = np.array([[[1], [2]], [[3], [4]]], dtype='float64')
    layer = image_preprocessing.RandomWidth(.2)
    self.assertAllEqual(layer(inputs).dtype, 'float32')
    layer = image_preprocessing.RandomWidth(.2, dtype='uint8')
    self.assertAllEqual(layer(inputs).dtype, 'uint8')


@test_combinations.run_all_keras_modes(always_skip_v1=True)
class LearningPhaseTest(test_combinations.TestCase):

  def test_plain_call(self):
    layer = image_preprocessing.RandomWidth(.5, seed=123)
    shape = (12, 12, 3)
    img = np.random.random((12,) + shape)
    out = layer(img)  # Default to training=True
    self.assertNotEqual(tuple(int(i) for i in out.shape[1:]), shape)

    out = layer(img, training=True)
    self.assertNotEqual(tuple(int(i) for i in out.shape[1:]), shape)

    out = layer(img, training=False)
    self.assertEqual(tuple(int(i) for i in out.shape[1:]), shape)

  def test_call_in_container(self):
    layer1 = image_preprocessing.RandomWidth(.5, seed=123)
    layer2 = image_preprocessing.RandomHeight(.5, seed=123)
    seq = sequential.Sequential([layer1, layer2])

    shape = (12, 12, 3)
    img = np.random.random((12,) + shape)
    out = seq(img)  # Default to training=True
    self.assertNotEqual(tuple(int(i) for i in out.shape[1:]), shape)

    out = seq(img, training=True)
    self.assertNotEqual(tuple(int(i) for i in out.shape[1:]), shape)

    out = seq(img, training=False)
    self.assertEqual(tuple(int(i) for i in out.shape[1:]), shape)


@test_combinations.run_all_keras_modes(always_skip_v1=True)
class DeterminismTest(test_combinations.TestCase):

  @parameterized.named_parameters(
      ('random_flip', image_preprocessing.RandomFlip),
      ('random_contrast',
       functools.partial(image_preprocessing.RandomContrast, factor=1.)),
      ('random_crop',
       functools.partial(image_preprocessing.RandomCrop, height=2, width=2)),
      ('random_translation',
       functools.partial(image_preprocessing.RandomTranslation, 0.3, 0.2)),
      ('random_rotation',
       functools.partial(image_preprocessing.RandomRotation, 0.5)),
      ('random_zoom', functools.partial(image_preprocessing.RandomZoom, 0.2)),
      ('random_height', functools.partial(image_preprocessing.RandomHeight,
                                          0.4)),
      ('random_width', functools.partial(image_preprocessing.RandomWidth, 0.3)),
  )
  def test_seed_constructor_arg(self, layer_cls):
    input_image = np.random.random((2, 5, 8, 3)).astype(np.float32)

    layer1 = layer_cls(seed=0.)
    layer2 = layer_cls(seed=0.)
    layer1_output = layer1(input_image)
    layer2_output = layer2(input_image)

    self.assertAllClose(layer1_output.numpy().tolist(),
                        layer2_output.numpy().tolist())


class RandomAddLayer(image_preprocessing.BaseImageAugmentationLayer):

  def __init__(self, value_range=(0., 1.0), fixed_value=None, **kwargs):
    super().__init__(**kwargs)
    self.value_range = value_range
    self.fixed_value = fixed_value

  def get_random_tranformation(self):
    if self.fixed_value:
      return self.fixed_value
    return self._random_generator.random_uniform(
        [], minval=self.value_range[0], maxval=self.value_range[1])

  def augment_image(self, image, transformation=None):
    return image + transformation

  def augment_label(self, label, transformation=None):
    return label + transformation


@test_combinations.run_all_keras_modes(always_skip_v1=True)
class BaseImageAugmentationLayerTest(test_combinations.TestCase):

  def test_augment_single_image(self):
    add_layer = RandomAddLayer(fixed_value=2.0)
    image = np.random.random(size=(8, 8, 3)).astype('float32')
    output = add_layer(image)

    self.assertAllClose(image + 2.0, output)

  def test_augment_batch_images(self):
    add_layer = RandomAddLayer()
    images = np.random.random(size=(2, 8, 8, 3)).astype('float32')
    output = add_layer(images)

    diff = output - images
    # Make sure the first image and second image get different augmentation
    self.assertNotAllClose(diff[0], diff[1])

  def test_augment_image_and_label(self):
    add_layer = RandomAddLayer(fixed_value=2.0)
    image = np.random.random(size=(8, 8, 3)).astype('float32')
    label = np.random.random(size=(1,)).astype('float32')

    output = add_layer({'images': image, 'labels': label})
    expected_output = {'images': image + 2.0, 'labels': label + 2.0}
    self.assertAllClose(output, expected_output)

  def test_augment_batch_images_and_labels(self):
    add_layer = RandomAddLayer()
    images = np.random.random(size=(2, 8, 8, 3)).astype('float32')
    labels = np.random.random(size=(2, 1)).astype('float32')
    output = add_layer({'images': images, 'labels': labels})

    image_diff = output['images'] - images
    label_diff = output['labels'] - labels
    # Make sure the first image and second image get different augmentation
    self.assertNotAllClose(image_diff[0], image_diff[1])
    self.assertNotAllClose(label_diff[0], label_diff[1])


if __name__ == '__main__':
  tf.test.main()
