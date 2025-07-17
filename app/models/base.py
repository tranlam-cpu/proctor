from typing import List, Optional

from sqlalchemy import DateTime, Double, Enum, Float, ForeignKeyConstraint, Index, Integer, JSON, String, TIMESTAMP, Text, text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime
import decimal

class Base(DeclarativeBase):
    pass


class Anhnhandien(Base):
    __tablename__ = 'anhnhandien'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    duong_dan_anh: Mapped[str] = mapped_column(Text)
    ma_sv: Mapped[Optional[str]] = mapped_column(String(20))
    thoi_gian: Mapped[Optional[datetime.datetime]] = mapped_column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    mo_ta_sai: Mapped[Optional[str]] = mapped_column(String(255))


class Chucnang(Base):
    __tablename__ = 'chucnang'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ten_chuc_nang: Mapped[str] = mapped_column(String(100))


class Dethi(Base):
    __tablename__ = 'dethi'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tieu_de: Mapped[Optional[str]] = mapped_column(String(255))
    mo_ta: Mapped[Optional[str]] = mapped_column(Text)
    cau_hoi: Mapped[Optional[dict]] = mapped_column(JSON)
    thoi_luong: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    trang_thai: Mapped[Optional[str]] = mapped_column(Enum('ready', 'start', 'end'))


class Nguoidung(Base):
    __tablename__ = 'nguoidung'

    ma_so: Mapped[str] = mapped_column(String(20), primary_key=True)
    ho_ten: Mapped[str] = mapped_column(String(100))
    email: Mapped[Optional[str]] = mapped_column(String(100))
    gioi_tinh: Mapped[Optional[int]] = mapped_column(TINYINT)

    nhandien: Mapped[List['Nhandien']] = relationship('Nhandien', back_populates='nguoi_dung')
    taikhoan: Mapped[List['Taikhoan']] = relationship('Taikhoan', back_populates='nguoi_dung')


class PhatHienGianLan(Base):
    __tablename__ = 'phathiengianlan'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))
    diem_gian_lan: Mapped[Optional[float]] = mapped_column(Float)
    diem_tuong_dong: Mapped[Optional[float]] = mapped_column(Float)
    duong_dan_anh: Mapped[Optional[str]] = mapped_column(Text)
    nguoi_dung_id: Mapped[Optional[str]] = mapped_column(String(20))
    nguoi_tao_id: Mapped[Optional[str]] = mapped_column(String(20))


class Phienthi(Base):
    __tablename__ = 'phienthi'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nguoi_dung_id: Mapped[Optional[str]] = mapped_column(String(20))
    de_thi_id: Mapped[Optional[int]] = mapped_column(Integer)
    thoi_gian_bat_dau: Mapped[Optional[datetime.datetime]] = mapped_column(TIMESTAMP)
    thoi_gian_ket_thuc: Mapped[Optional[datetime.datetime]] = mapped_column(TIMESTAMP)
    diem: Mapped[Optional[float]] = mapped_column(Float)


class Phongthi(Base):
    __tablename__ = 'phongthi'

    ma_phong: Mapped[str] = mapped_column(String(20), primary_key=True)
    ten_phong: Mapped[str] = mapped_column(String(100))
    trang_thai: Mapped[Optional[str]] = mapped_column(Enum('chua_bat_dau', 'dang_thi', 'da_ket_thuc'), server_default=text("'chua_bat_dau'"))
    thoi_gian_bat_dau: Mapped[Optional[datetime.datetime]] = mapped_column(TIMESTAMP)
    thoi_gian_ket_thuc: Mapped[Optional[datetime.datetime]] = mapped_column(TIMESTAMP)


class Thamgiathi(Base):
    __tablename__ = 'thamgiathi'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ma_sv: Mapped[Optional[str]] = mapped_column(String(20))
    dinh_danh_luc: Mapped[Optional[datetime.datetime]] = mapped_column(TIMESTAMP)
    so_lan_sai_lien_tiep: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("'0'"))
    trang_thai: Mapped[Optional[str]] = mapped_column(Enum('cho', 'dang_thi', 'da_thi'), server_default=text("'cho'"))


class Vaitro(Base):
    __tablename__ = 'vaitro'
    __table_args__ = (
        Index('ten_vai_tro', 'ten_vai_tro', unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ten_vai_tro: Mapped[str] = mapped_column(String(50))

    chucnang_quyen_vaitro: Mapped[List['ChucnangQuyenVaitro']] = relationship('ChucnangQuyenVaitro', back_populates='vai_tro')
    taikhoan: Mapped[List['Taikhoan']] = relationship('Taikhoan', back_populates='vai_tro')


class ChucnangQuyenVaitro(Base):
    __tablename__ = 'chucnang_quyen_vaitro'
    __table_args__ = (
        ForeignKeyConstraint(['vai_tro_id'], ['vaitro.id'], ondelete='CASCADE', onupdate='CASCADE', name='chucnang_quyen_vaitro_ibfk_1'),
        Index('vai_tro_id', 'vai_tro_id')
    )

    chuc_nang_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    bitwise: Mapped[int] = mapped_column(Integer, server_default=text("'0'"))
    vai_tro_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    vai_tro: Mapped['Vaitro'] = relationship('Vaitro', back_populates='chucnang_quyen_vaitro')


class Nhandien(Base):
    __tablename__ = 'nhandien'
    __table_args__ = (
        ForeignKeyConstraint(['nguoi_dung_id'], ['nguoidung.ma_so'], name='nhandien_ibfk_1'),
        Index('nguoi_dung_id', 'nguoi_dung_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    embedding_vector: Mapped[str] = mapped_column(Text)
    nguoi_dung_id: Mapped[Optional[str]] = mapped_column(String(20))
    duong_dan_anh: Mapped[Optional[str]] = mapped_column(Text)
    danh_gia: Mapped[Optional[decimal.Decimal]] = mapped_column(Double(asdecimal=True))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))

    nguoi_dung: Mapped[Optional['Nguoidung']] = relationship('Nguoidung', back_populates='nhandien')


class Taikhoan(Base):
    __tablename__ = 'taikhoan'
    __table_args__ = (
        ForeignKeyConstraint(['nguoi_dung_id'], ['nguoidung.ma_so'], ondelete='CASCADE', name='taikhoan_ibfk_2'),
        ForeignKeyConstraint(['vai_tro_id'], ['vaitro.id'], name='taikhoan_ibfk_1'),
        Index('nguoi_dung_id', 'nguoi_dung_id'),
        Index('taikhoan_ibfk_1', 'vai_tro_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mat_khau: Mapped[str] = mapped_column(String(255))
    vai_tro_id: Mapped[Optional[int]] = mapped_column(Integer)
    nguoi_dung_id: Mapped[Optional[str]] = mapped_column(String(20))

    nguoi_dung: Mapped[Optional['Nguoidung']] = relationship('Nguoidung', back_populates='taikhoan')
    vai_tro: Mapped[Optional['Vaitro']] = relationship('Vaitro', back_populates='taikhoan')
    refreshtokens: Mapped[List['Refreshtokens']] = relationship('Refreshtokens', back_populates='tai_khoan')


class Refreshtokens(Base):
    __tablename__ = 'refreshtokens'
    __table_args__ = (
        ForeignKeyConstraint(['tai_khoan_id'], ['taikhoan.id'], name='refreshtokens_ibfk_1'),
        Index('tai_khoan_id', 'tai_khoan_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[Optional[str]] = mapped_column(String(255))
    thoi_han: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    thu_hoi: Mapped[Optional[int]] = mapped_column(TINYINT(1))
    tai_khoan_id: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    tai_khoan: Mapped[Optional['Taikhoan']] = relationship('Taikhoan', back_populates='refreshtokens')
